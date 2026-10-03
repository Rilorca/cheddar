use ksni::{menu::*, Category, Handle, ToolTip, Tray, TrayMethods};
use log::{debug, error, info};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Clone)]
pub struct TrayState {
    pub enabled: bool,
    pub active_target_name: Option<String>,
    pub current_dpi: Option<u32>,
    pub active_exe: Option<String>,
    pub battery_percentage: Option<u32>,
}

impl Default for TrayState {
    fn default() -> Self {
        Self {
            enabled: false,
            active_target_name: None,
            current_dpi: None,
            active_exe: None,
            battery_percentage: None,
        }
    }
}

pub struct CheddarTray {
    pub state: Arc<Mutex<TrayState>>,
    pub cached: TrayState,
}

impl CheddarTray {
    pub fn new(initial_state: Arc<Mutex<TrayState>>, initial_cached: TrayState) -> Self {
        Self {
            state: initial_state,
            cached: initial_cached,
        }
    }

    pub fn format_tooltip_title() -> String {
        "Cheddar AutoPilot".to_string()
    }

    pub fn format_tooltip_description(state: &TrayState) -> String {
        if !state.enabled {
            return "AutoPilot desactivado".to_string();
        }

        let mut parts = Vec::new();
        if let Some(target) = &state.active_target_name {
            parts.push(format!("Perfil: {}", target));
        }
        if let Some(exe) = &state.active_exe {
            parts.push(format!("Juego: {}", exe));
        }
        if let Some(dpi) = state.current_dpi {
            parts.push(format!("{} DPI", dpi));
        }
        if let Some(battery) = state.battery_percentage {
            parts.push(format!("Batería: {}%", battery));
        }

        if parts.is_empty() {
            "AutoPilot activo".to_string()
        } else {
            parts.join(" • ")
        }
    }
}

impl Tray for CheddarTray {
    fn id(&self) -> String {
        "cheddar-autopilot".to_string()
    }

    fn category(&self) -> Category {
        Category::Hardware
    }

    fn title(&self) -> String {
        "Cheddar AutoPilot".to_string()
    }

    fn icon_name(&self) -> String {
        "input-mouse".to_string()
    }

    fn tool_tip(&self) -> ToolTip {
        ToolTip {
            title: Self::format_tooltip_title(),
            description: Self::format_tooltip_description(&self.cached),
            icon_name: "input-mouse".to_string(),
            icon_pixmap: Vec::new(),
        }
    }

    fn activate(&mut self, _x: i32, _y: i32) {
        info!("Tray activated (left-click): launching Cheddar GUI");
        tokio::spawn(async {
            let res = tokio::process::Command::new("cheddar").spawn();
            if let Err(e) = res {
                error!("Failed to launch cheddar GUI: {}", e);
            }
        });
    }

    fn menu(&self) -> Vec<MenuItem<Self>> {
        let mut items = Vec::new();

        // 1. Open Cheddar GUI
        items.push(
            StandardItem {
                label: "Abrir Cheddar".to_string(),
                icon_name: "preferences-desktop-peripherals".to_string(),
                activate: Box::new(|_| {
                    info!("Menu clicked: Abrir Cheddar");
                    tokio::spawn(async {
                        let _ = tokio::process::Command::new("cheddar").spawn();
                    });
                }),
                ..Default::default()
            }
            .into(),
        );

        items.push(MenuItem::Separator);

        // 2. Checkmark: AutoPilot Enabled / Disabled
        let is_enabled = self.cached.enabled;
        let shared_state = Arc::clone(&self.state);
        items.push(
            CheckmarkItem {
                label: "AutoPilot Activado".to_string(),
                checked: is_enabled,
                activate: Box::new(move |this: &mut Self| {
                    let new_state = !this.cached.enabled;
                    this.cached.enabled = new_state;
                    info!("Tray toggled AutoPilot: enabled = {}", new_state);
                    let shared = Arc::clone(&shared_state);
                    tokio::spawn(async move {
                        // Update config file
                        let mut cfg = crate::config::load_config();
                        cfg.enabled = new_state;
                        if let Err(e) = crate::config::save_config(&cfg) {
                            error!("Failed to save config from tray toggle: {}", e);
                        }
                        let mut st = shared.lock().await;
                        st.enabled = new_state;
                    });
                }),
                ..Default::default()
            }
            .into(),
        );

        // 3. Current Profile Info
        let profile_label = match &self.cached.active_target_name {
            Some(name) => format!("Perfil: {}", name),
            None => "Perfil: Por defecto".to_string(),
        };
        items.push(
            StandardItem {
                label: profile_label,
                enabled: false,
                icon_name: "view-paged-symbolic".to_string(),
                ..Default::default()
            }
            .into(),
        );

        // 4. Current DPI Info
        if let Some(dpi) = self.cached.current_dpi {
            items.push(
                StandardItem {
                    label: format!("DPI: {}", dpi),
                    enabled: false,
                    icon_name: "input-mouse".to_string(),
                    ..Default::default()
                }
                .into(),
            );
        }

        // 5. Active Game / Process Info (if running)
        if let Some(exe) = &self.cached.active_exe {
            items.push(
                StandardItem {
                    label: format!("Juego: {}", exe),
                    enabled: false,
                    icon_name: "applications-games".to_string(),
                    ..Default::default()
                }
                .into(),
            );
        }

        // 6. Battery (if known)
        if let Some(battery) = self.cached.battery_percentage {
            items.push(
                StandardItem {
                    label: format!("Batería: {}%", battery),
                    enabled: false,
                    icon_name: "battery-good-symbolic".to_string(),
                    ..Default::default()
                }
                .into(),
            );
        }

        items.push(MenuItem::Separator);

        // 7. Restart Daemon / Reload
        items.push(
            StandardItem {
                label: "Recargar Reglas".to_string(),
                icon_name: "view-refresh".to_string(),
                activate: Box::new(|_| {
                    info!("Tray menu: Recargar Reglas clicked");
                    let cfg = crate::config::load_config();
                    debug!("Config reloaded manually: {:?}", cfg);
                }),
                ..Default::default()
            }
            .into(),
        );

        items
    }
}

pub async fn spawn_tray(
    state: Arc<Mutex<TrayState>>,
    initial_cached: TrayState,
) -> Result<Handle<CheddarTray>, Box<dyn std::error::Error + Send + Sync>> {
    let tray = CheddarTray::new(state, initial_cached);
    let handle = tray.spawn().await?;
    info!("StatusNotifierItem System Tray spawned successfully");
    Ok(handle)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_tooltip_disabled() {
        let state = TrayState {
            enabled: false,
            active_target_name: Some("Gaming".to_string()),
            current_dpi: Some(1200),
            active_exe: None,
            battery_percentage: None,
        };
        assert_eq!(
            CheddarTray::format_tooltip_description(&state),
            "AutoPilot desactivado"
        );
    }

    #[test]
    fn test_format_tooltip_enabled_full() {
        let state = TrayState {
            enabled: true,
            active_target_name: Some("Dota 2".to_string()),
            current_dpi: Some(1600),
            active_exe: Some("dota2".to_string()),
            battery_percentage: Some(85),
        };
        let desc = CheddarTray::format_tooltip_description(&state);
        assert!(desc.contains("Perfil: Dota 2"));
        assert!(desc.contains("Juego: dota2"));
        assert!(desc.contains("1600 DPI"));
        assert!(desc.contains("Batería: 85%"));
    }

    #[test]
    fn test_format_tooltip_enabled_minimal() {
        let state = TrayState {
            enabled: true,
            active_target_name: None,
            current_dpi: None,
            active_exe: None,
            battery_percentage: None,
        };
        assert_eq!(
            CheddarTray::format_tooltip_description(&state),
            "AutoPilot activo"
        );
    }

    #[test]
    fn test_menu_generation() {
        let state = Arc::new(Mutex::new(TrayState {
            enabled: true,
            active_target_name: Some("Work".to_string()),
            current_dpi: Some(800),
            active_exe: None,
            battery_percentage: None,
        }));
        let cached = TrayState {
            enabled: true,
            active_target_name: Some("Work".to_string()),
            current_dpi: Some(800),
            active_exe: None,
            battery_percentage: None,
        };
        let tray = CheddarTray::new(state, cached);

        let menu = tray.menu();
        assert!(!menu.is_empty());
        assert_eq!(tray.id(), "cheddar-autopilot");
        assert_eq!(tray.title(), "Cheddar AutoPilot");
        assert_eq!(tray.icon_name(), "input-mouse");
    }
}
