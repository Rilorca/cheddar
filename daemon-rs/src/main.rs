mod config;
mod notify;
mod process;
mod ratbag;
mod tray;

use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use log::{debug, error, info, warn};

use config::{config_path, load_config, AutoPilotConfig, RuleTarget};
use notify::Notifier;
use process::{focused_pid, scan_processes};
use ratbag::RatbagClient;
use tray::{spawn_tray, TrayState};

const TICK_INTERVAL: Duration = Duration::from_millis(250);
const PROCESS_SCAN_TICKS: u32 = 6; // 6 * 250ms = 1500ms for process scanning

struct WatcherState {
    config: AutoPilotConfig,
    active_target: Option<RuleTarget>,
    last_matched_exe: Option<String>,
    is_asleep: bool,
    pre_sleep_target: Option<RuleTarget>,
    last_reported_dpi: HashMap<String, u32>,
    low_battery_notified: HashSet<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    info!("Starting Cheddar AutoPilot daemon (Rust native v0.8.0)");

    let notifier = Arc::new(Notifier::new().await);

    let mut ratbag_client: Option<RatbagClient> = match RatbagClient::connect().await {
        Ok(client) => {
            info!("Connected to system D-Bus / ratbagd");
            Some(client)
        }
        Err(e) => {
            warn!("Could not connect to ratbagd immediately: {}. Will connect when available.", e);
            None
        }
    };

    let initial_config = load_config();
    let initial_light = tray::is_light_theme();
    let initial_tray_state = TrayState {
        enabled: initial_config.enabled,
        active_target_name: Some(format!("Perfil {}", initial_config.default_profile + 1)),
        current_dpi: None,
        active_exe: None,
        battery_percentage: None,
        is_light: initial_light,
    };
    let tray_handle = match spawn_tray(initial_tray_state).await {
        Ok(handle) => {
            info!("System Tray icon initialized (StatusNotifierItem, light_mode={})", initial_light);
            Some(handle)
        }
        Err(e) => {
            warn!("Could not initialize System Tray icon: {}", e);
            None
        }
    };

    let state = Arc::new(Mutex::new(WatcherState {
        config: initial_config,
        active_target: None,
        last_matched_exe: None,
        is_asleep: false,
        pre_sleep_target: None,
        last_reported_dpi: HashMap::new(),
        low_battery_notified: HashSet::new(),
    }));

    // Setup config file watcher using tokio task
    let state_for_file_watcher = Arc::clone(&state);
    let tray_handle_for_file_watcher = tray_handle.clone();
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
                        let is_enabled = new_cfg.enabled;
                        let mut st = state_for_file_watcher.lock().await;
                        st.config = new_cfg;
                        st.active_target = None; // Trigger re-evaluation
                        info!(
                            "Config reloaded: {} rule(s), default profile {}, enabled: {}",
                            st.config.rules.len(),
                            st.config.default_profile,
                            st.config.enabled
                        );
                        if let Some(th) = &tray_handle_for_file_watcher {
                            let _ = th.update(|t| {
                                t.cached.enabled = is_enabled;
                            }).await;
                        }
                    }
                }
            }
        }
    });

    // Main polling loop
    let mut interval = tokio::time::interval(TICK_INTERVAL);
    let mut tick_count: u32 = 0;

    loop {
        interval.tick().await;
        tick_count = tick_count.wrapping_add(1);

        let (enabled, rules, default_profile, notifications_enabled, config_clone) = {
            let st = state.lock().await;
            (
                st.config.enabled,
                st.config.rules.clone(),
                st.config.default_profile,
                st.config.notifications_enabled,
                st.config.clone(),
            )
        };

        if !enabled {
            continue;
        }

        if ratbag_client.is_none() {
            ratbag_client = RatbagClient::connect().await.ok();
        }

        // Feature 5: Fast DPI switch / OSD notification check (every 250ms)
        if let Some(client) = &ratbag_client {
            if let Ok(devices) = client.list_device_paths().await {
                for dev_path in &devices {
                    let dev_name = client
                        .get_device_name(dev_path)
                        .await
                        .unwrap_or_else(|_| "Mouse".to_string());

                    if let Ok(Some(current_dpi)) = client.get_active_dpi(dev_path).await {
                        let mut st = state.lock().await;
                        let last_dpi = st.last_reported_dpi.get(&dev_name).copied();
                        let changed = match last_dpi {
                            Some(prev) => prev != current_dpi,
                            None => true,
                        };
                        if changed {
                            st.last_reported_dpi.insert(dev_name.clone(), current_dpi);
                            if last_dpi.is_some() && notifications_enabled {
                                let summary = format!("DPI: {}", current_dpi);
                                let body = format!("{}: Sensibilidad ajustada", dev_name);
                                notifier.notify(&summary, &body, "input-mouse", 1500).await;
                            }
                            if let Some(th) = &tray_handle {
                                let _ = th.update(|t| {
                                    t.cached.current_dpi = Some(current_dpi);
                                }).await;
                            }
                        }
                    }
                }
            }
        }

        // Heavy checks: Run screen lock check, battery check, and process scanning every 1500ms
        if tick_count % PROCESS_SCAN_TICKS != 0 {
            continue;
        }

        // Feature 4: Sleep / ScreenSaver detection
        let is_screen_locked = notifier.is_screen_saver_active().await;
        {
            let mut st = state.lock().await;
            if is_screen_locked && !st.is_asleep {
                st.is_asleep = true;
                st.pre_sleep_target = st.active_target.clone();
                debug!("Screen locked / idle detected: entering AutoPilot sleep state");
            } else if !is_screen_locked && st.is_asleep {
                st.is_asleep = false;
                st.active_target = None; // Force re-evaluation & restore active profile
                info!("Screen unlocked: waking up and restoring active profile");
            }
        }

        // Feature 3: Battery check
        if let Some(client) = &ratbag_client {
            if let Ok(devices) = client.list_device_paths().await {
                for dev_path in &devices {
                    let dev_name = client
                        .get_device_name(dev_path)
                        .await
                        .unwrap_or_else(|_| "Mouse".to_string());

                    if let Ok(Some(battery_pct)) = client.get_battery(dev_path).await {
                        if let Some(th) = &tray_handle {
                            let _ = th.update(|t| {
                                t.cached.battery_percentage = Some(battery_pct);
                            }).await;
                        }
                        let mut st = state.lock().await;
                        if battery_pct <= 15 && !st.low_battery_notified.contains(&dev_name) {
                            st.low_battery_notified.insert(dev_name.clone());
                            if notifications_enabled {
                                let summary = format!("⚠️ Batería Baja: {}", dev_name);
                                let body = format!("El nivel de batería es {}%. Conecta el cable o base de carga.", battery_pct);
                                notifier.notify(&summary, &body, "battery-caution", 6000).await;
                            }
                        } else if battery_pct > 25 {
                            st.low_battery_notified.remove(&dev_name);
                        }
                    }
                }
            }
        }

        // Theme check: detect light/dark changes dynamically in KDE/GNOME
        let current_light = tray::is_light_theme();
        if let Some(th) = &tray_handle {
            let _ = th.update(|t| {
                if t.cached.is_light != current_light {
                    t.cached.is_light = current_light;
                }
            }).await;
        }

        if rules.is_empty() {
            continue;
        }

        let procs = scan_processes();
        let mut matched_target: Option<RuleTarget> = None;
        let mut matched_exe: Option<String> = None;

        let mut all_running = HashSet::new();
        for names in procs.values() {
            all_running.extend(names.clone());
        }

        // If Cheddar GUI is open and configuring the mouse, don't force switch to default profile!
        let is_cheddar_running = all_running.iter().any(|name| {
            let n = name.to_lowercase();
            n.contains("cheddar") || n.contains("piper")
        });

        let focused = focused_pid();
        if let Some(f_pid) = focused {
            let focused_names = if f_pid > 0 {
                procs.get(&f_pid).cloned().unwrap_or_default()
            } else {
                HashSet::new()
            };

            // If the Cheddar GUI is currently focused, do not override what the user is configuring!
            let is_cheddar_focused = focused_names.iter().any(|name| {
                let n = name.to_lowercase();
                n.contains("cheddar") || n.contains("piper")
            });
            if is_cheddar_focused {
                continue;
            }

            for (exe, target) in &rules {
                let clean_exe = exe.to_lowercase();
                let no_space = clean_exe.replace(' ', "");
                if focused_names.contains(&clean_exe) || focused_names.contains(&no_space) {
                    matched_target = Some(target.clone());
                    matched_exe = Some(exe.clone());
                    break;
                }
            }
        }

        // Fallback matching when focus-matching did not find a rule (e.g. Wayland or background check)
        if matched_target.is_none() {
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

        // If no game matched and Cheddar GUI is open, do not force-switch to default profile!
        if is_cheddar_running && matched_target.is_none() {
            continue;
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

            if let Some(th) = &tray_handle {
                let target_str = match &final_target {
                    RuleTarget::Index(idx) => format!("Perfil {}", idx + 1),
                    RuleTarget::Software(name) => name.strip_prefix("sw:").unwrap_or(name).to_string(),
                };
                let exe_str = if exe_label != "__default__" {
                    Some(exe_label.clone())
                } else {
                    None
                };
                let _ = th.update(|t| {
                    t.cached.active_target_name = Some(target_str);
                    t.cached.active_exe = exe_str;
                }).await;
            }

            if let Some(client) = &ratbag_client {
                match client.list_device_paths().await {
                    Ok(devices) => {
                        for dev_path in devices {
                            let dev_name = client
                                .get_device_name(&dev_path)
                                .await
                                .unwrap_or_else(|_| "Unknown Device".to_string());

                            if let Err(e) = client
                                .activate_target(&dev_path, &final_target, &config_clone)
                                .await
                            {
                                error!("Failed to switch profile on {}: {}", dev_name, e);
                            } else {
                                info!("Successfully switched {} to {}", dev_name, final_target);

                                // Feature 1: Native Desktop Notification on profile switch
                                if notifications_enabled {
                                    let target_str = match &final_target {
                                        RuleTarget::Index(idx) => format!("Perfil Onboard {}", idx + 1),
                                        RuleTarget::Software(name) => {
                                            name.strip_prefix("sw:").unwrap_or(name).to_string()
                                        }
                                    };

                                    let summary = if exe_label == "__default__" {
                                        "Perfil Predeterminado".to_string()
                                    } else {
                                        format!("🎮 {}", exe_label)
                                    };

                                    let body = format!("{}: {}", dev_name, target_str);
                                    notifier.notify(&summary, &body, "input-mouse", 2500).await;
                                }
                            }
                        }
                    }
                    Err(e) => {
                        error!("Error listing ratbag devices: {}. Resetting connection.", e);
                        ratbag_client = None;
                    }
                }
            } else {
                warn!("ratbagd is unavailable; switch deferred to next tick.");
                let mut st = state.lock().await;
                st.active_target = None; // Retry on next tick
            }
        }
    }
}
