mod config;
mod process;
mod ratbag;

use std::collections::HashSet;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use log::{error, info, warn};

use config::{config_path, load_config, AutoPilotConfig, RuleTarget};
use process::{focused_pid, scan_processes};
use ratbag::RatbagClient;

const POLL_INTERVAL: Duration = Duration::from_millis(2000);

struct WatcherState {
    config: AutoPilotConfig,
    active_target: Option<RuleTarget>,
    last_matched_exe: Option<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    info!("Starting Cheddar AutoPilot daemon (Rust native v0.8.0)");

    let ratbag_client = match RatbagClient::connect().await {
        Ok(client) => {
            info!("Connected to system D-Bus / ratbagd");
            Arc::new(client)
        }
        Err(e) => {
            warn!("Could not connect to ratbagd immediately: {}. Will retry during ticks.", e);
            // We can still run and try to connect lazily
            return Err(e.into());
        }
    };

    let state = Arc::new(Mutex::new(WatcherState {
        config: load_config(),
        active_target: None,
        last_matched_exe: None,
    }));

    // Setup config file watcher using tokio task
    let state_for_file_watcher = Arc::clone(&state);
    tokio::spawn(async move {
        let mut last_modified = None;
        let path = config_path();

        loop {
            tokio::time::sleep(Duration::from_millis(1500)).await;
            if let Ok(metadata) = std::fs::metadata(&path) {
                if let Ok(modified) = metadata.modified() {
                    if last_modified != Some(modified) {
                        last_modified = Some(modified);
                        let new_cfg = load_config();
                        let mut st = state_for_file_watcher.lock().await;
                        st.config = new_cfg;
                        st.active_target = None; // Trigger re-evaluation
                        info!(
                            "Config reloaded: {} rule(s), default profile {}, enabled: {}",
                            st.config.rules.len(),
                            st.config.default_profile,
                            st.config.enabled
                        );
                    }
                }
            }
        }
    });

    // Main polling loop
    let mut interval = tokio::time::interval(POLL_INTERVAL);

    loop {
        interval.tick().await;

        let (enabled, rules, default_profile, config_clone) = {
            let st = state.lock().await;
            (
                st.config.enabled,
                st.config.rules.clone(),
                st.config.default_profile,
                st.config.clone(),
            )
        };

        if !enabled || rules.is_empty() {
            continue;
        }

        let procs = scan_processes();
        let mut matched_target: Option<RuleTarget> = None;
        let mut matched_exe: Option<String> = None;

        let focused = focused_pid();
        if let Some(f_pid) = focused {
            let focused_names = if f_pid > 0 {
                procs.get(&f_pid).cloned().unwrap_or_default()
            } else {
                HashSet::new()
            };

            for (exe, target) in &rules {
                let clean_exe = exe.to_lowercase();
                let no_space = clean_exe.replace(' ', "");
                if focused_names.contains(&clean_exe) || focused_names.contains(&no_space) {
                    matched_target = Some(target.clone());
                    matched_exe = Some(exe.clone());
                    break;
                }
            }
        } else {
            // Fallback when focus cannot be determined: any running process
            let mut all_running = HashSet::new();
            for names in procs.values() {
                all_running.extend(names.clone());
            }

            let last_exe = { state.lock().await.last_matched_exe.clone() };
            if let Some(last) = last_exe {
                let clean_last = last.to_lowercase();
                if all_running.contains(&clean_last) || all_running.contains(&clean_last.replace(' ', "")) {
                    if let Some(target) = rules.get(&last) {
                        matched_target = Some(target.clone());
                        matched_exe = Some(last);
                    }
                }
            }

            if matched_target.is_none() {
                for (exe, target) in &rules {
                    let clean_exe = exe.to_lowercase();
                    let no_space = clean_exe.replace(' ', "");
                    if all_running.contains(&clean_exe) || all_running.contains(&no_space) {
                        matched_target = Some(target.clone());
                        matched_exe = Some(exe.clone());
                        break;
                    }
                }
            }
        }

        let final_target = matched_target.unwrap_or(RuleTarget::Index(default_profile));
        let exe_label = matched_exe.unwrap_or_else(|| "__default__".to_string());

        let need_switch = {
            let mut st = state.lock().await;
            st.last_matched_exe = if exe_label != "__default__" {
                Some(exe_label.clone())
            } else {
                None
            };

            if st.active_target.as_ref() != Some(&final_target) {
                st.active_target = Some(final_target.clone());
                true
            } else {
                false
            }
        };

        if need_switch {
            info!("AutoPilot switch: '{}' -> target {}", exe_label, final_target);

            match ratbag_client.list_device_paths().await {
                Ok(devices) => {
                    for dev_path in devices {
                        let dev_name = ratbag_client
                            .get_device_name(&dev_path)
                            .await
                            .unwrap_or_else(|_| "Unknown Device".to_string());

                        if let Err(e) = ratbag_client
                            .activate_target(&dev_path, &final_target, &config_clone)
                            .await
                        {
                            error!("Failed to switch profile on {}: {}", dev_name, e);
                        } else {
                            info!("Successfully switched {} to {}", dev_name, final_target);
                        }
                    }
                }
                Err(e) => {
                    error!("Error listing ratbag devices: {}", e);
                }
            }
        }
    }
}
