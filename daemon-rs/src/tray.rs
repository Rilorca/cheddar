use ksni::{menu::*, Category, Handle, ToolTip, Tray, TrayMethods};
use log::{error, info};

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
    pub cached: TrayState,
}

impl CheddarTray {
    pub fn new(initial_cached: TrayState) -> Self {
        Self {
            cached: initial_cached,
        }
    }

    pub fn format_tooltip_title() -> String {
        "Cheddar AutoPilot".to_string()
    }

    pub fn format_tooltip_description(state: &TrayState) -> String {
        let profile_str = state
            .active_target_name
            .as_deref()
            .unwrap_or("Por defecto");

        let dpi_str = match state.current_dpi {
            Some(dpi) => format!("{} DPI", dpi),
            None => "DPI: --".to_string(),
        };

        if let Some(exe) = &state.active_exe {
            format!("Perfil: {} ({})\nDPI: {}", profile_str, exe, dpi_str)
        } else {
            format!("Perfil: {}\nDPI: {}", profile_str, dpi_str)
        }
    }
}

use std::sync::LazyLock;
use image::GenericImageView;

static TRAY_ICON_PIXMAP_LIGHT: LazyLock<ksni::Icon> = LazyLock::new(|| {
    let img = image::load_from_memory_with_format(
        include_bytes!("../../data/icons/tray/cheddar-tray-symbolic.png"),
        image::ImageFormat::Png,
    )
    .expect("valid cheddar-tray-symbolic.png");
    let (width, height) = img.dimensions();
    let mut data = img.into_rgba8().into_vec();
    for pixel in data.chunks_exact_mut(4) {
        pixel.rotate_right(1); // RGBA to ARGB
    }
    ksni::Icon {
        width: width as i32,
        height: height as i32,
        data,
    }
});

static TRAY_ICON_PIXMAP_DARK: LazyLock<ksni::Icon> = LazyLock::new(|| {
    let img = image::load_from_memory_with_format(
        include_bytes!("../../data/icons/tray/cheddar-tray-dark.png"),
        image::ImageFormat::Png,
    )
    .expect("valid cheddar-tray-dark.png");
    let (width, height) = img.dimensions();
    let mut data = img.into_rgba8().into_vec();
    for pixel in data.chunks_exact_mut(4) {
        pixel.rotate_right(1); // RGBA to ARGB
    }
    ksni::Icon {
        width: width as i32,
        height: height as i32,
        data,
    }
});

pub fn is_light_theme() -> bool {
    // 1. Try reading KDE's ColorScheme config
    if let Ok(output) = std::process::Command::new("kreadconfig6")
        .args(["--group", "General", "--key", "ColorScheme"])
        .output()
    {
        let s = String::from_utf8_lossy(&output.stdout).to_lowercase();
        if s.contains("light") {
            return true;
        }
        if s.contains("dark") {
            return false;
        }
    }

    // 2. Try XDG Portal via D-Bus / busctl
    if let Ok(output) = std::process::Command::new("busctl")
        .args([
            "--user",
            "call",
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Settings",
            "Read",
            "ss",
            "org.freedesktop.appearance",
            "color-scheme",
        ])
        .output()
    {
        let s = String::from_utf8_lossy(&output.stdout);
        // Portal returns: 1 = prefer dark, 2 = prefer light
        if s.contains(" 2") {
            return true;
        }
        if s.contains(" 1") {
            return false;
        }
    }

    false
}

fn launch_cheddar_gui() {
    let binary = dirs::home_dir()
        .map(|h| h.join(".local/bin/cheddar"))
        .filter(|p| p.exists())
        .unwrap_or_else(|| std::path::PathBuf::from("cheddar"));

    info!("Launching Cheddar GUI: {:?}", binary);
    let res = tokio::process::Command::new(binary).spawn();
    if let Err(e) = res {
        error!("Failed to launch Cheddar GUI: {}", e);
    }
}

impl Tray for CheddarTray {
    fn id(&self) -> String {
        "io.github.rilorca.Cheddar".to_string()
    }

    fn category(&self) -> Category {
        Category::Hardware
    }

    fn title(&self) -> String {
        "Cheddar".to_string()
    }

    fn icon_name(&self) -> String {
        "io.github.rilorca.Cheddar-symbolic".to_string()
    }

    fn icon_theme_path(&self) -> String {
        dirs::data_local_dir()
            .map(|p| p.join("icons").to_string_lossy().to_string())
            .unwrap_or_else(|| "/home/rodrigo/.local/share/icons".to_string())
    }

    fn icon_pixmap(&self) -> Vec<ksni::Icon> {
        if is_light_theme() {
            vec![TRAY_ICON_PIXMAP_DARK.clone()]
        } else {
            vec![TRAY_ICON_PIXMAP_LIGHT.clone()]
        }
    }

    fn tool_tip(&self) -> ToolTip {
        let pixmap = if is_light_theme() {
            vec![TRAY_ICON_PIXMAP_DARK.clone()]
        } else {
            vec![TRAY_ICON_PIXMAP_LIGHT.clone()]
        };

        ToolTip {
            title: Self::format_tooltip_title(),
            description: Self::format_tooltip_description(&self.cached),
            icon_name: "io.github.rilorca.Cheddar-symbolic".to_string(),
            icon_pixmap: pixmap,
        }
    }

    fn activate(&mut self, _x: i32, _y: i32) {
        info!("Tray activated (left-click): launching Cheddar GUI");
        tokio::spawn(async {
            launch_cheddar_gui();
        });
    }

    fn menu(&self) -> Vec<MenuItem<Self>> {
        let mut items = Vec::new();

        // 1. Abrir Cheddar
        items.push(
            StandardItem {
                label: "Abrir Cheddar".to_string(),
                icon_name: "io.github.rilorca.Cheddar".to_string(),
                activate: Box::new(|_| {
                    info!("Menu clicked: Abrir Cheddar");
                    tokio::spawn(async {
                        launch_cheddar_gui();
                    });
                }),
                ..Default::default()
            }
            .into(),
        );

        // 2. Cerrar Cheddar (cierra GUI y detiene el proceso completo)
        items.push(
            StandardItem {
                label: "Cerrar Cheddar".to_string(),
                icon_name: "application-exit".to_string(),
                activate: Box::new(|_| {
                    info!("Menu clicked: Cerrar Cheddar (terminando GUI y servicio)");
                    tokio::spawn(async {
                        // 1. Matar cualquier ventana o proceso GUI de Cheddar abierto
                        let _ = tokio::process::Command::new("pkill")
                            .args(["-f", "python3 .*cheddar"])
                            .status()
                            .await;

                        // 2. Detener el servicio systemd del daemon
                        let _ = tokio::process::Command::new("systemctl")
                            .args(["--user", "stop", "cheddar-autopilot.service"])
                            .status()
                            .await;

                        // 3. Fallback de salida limpia del proceso actual
                        std::process::exit(0);
                    });
                }),
                ..Default::default()
            }
            .into(),
        );

        items.push(MenuItem::Separator);

        // Fila 1: El perfil actual
        let profile_display = match &self.cached.active_target_name {
            Some(name) => {
                if let Some(exe) = &self.cached.active_exe {
                    format!("Perfil: {} ({})", name, exe)
                } else {
                    format!("Perfil: {}", name)
                }
            }
            None => "Perfil: Por defecto".to_string(),
        };
        items.push(
            StandardItem {
                label: profile_display,
                enabled: false,
                icon_name: "view-paged-symbolic".to_string(),
                ..Default::default()
            }
            .into(),
        );

        // Fila 2: El DPI activo
        let dpi_display = match self.cached.current_dpi {
            Some(dpi) => format!("DPI: {} DPI", dpi),
            None => "DPI: --".to_string(),
        };
        items.push(
            StandardItem {
                label: dpi_display,
                enabled: false,
                icon_name: "input-mouse".to_string(),
                ..Default::default()
            }
            .into(),
        );

        items
    }
}

pub async fn spawn_tray(
    initial_cached: TrayState,
) -> Result<Handle<CheddarTray>, Box<dyn std::error::Error + Send + Sync>> {
    let tray = CheddarTray::new(initial_cached);
    let handle = tray.spawn().await?;
    info!("StatusNotifierItem System Tray spawned successfully with cheese icon");
    Ok(handle)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_tooltip_description() {
        let state = TrayState {
            enabled: true,
            active_target_name: Some("Dota 2".to_string()),
            current_dpi: Some(1600),
            active_exe: Some("dota2".to_string()),
            battery_percentage: None,
        };
        let desc = CheddarTray::format_tooltip_description(&state);
        assert!(desc.contains("Perfil: Dota 2 (dota2)"));
        assert!(desc.contains("DPI: 1600 DPI"));
    }

    #[test]
    fn test_format_tooltip_default() {
        let state = TrayState {
            enabled: true,
            active_target_name: None,
            current_dpi: Some(800),
            active_exe: None,
            battery_percentage: None,
        };
        let desc = CheddarTray::format_tooltip_description(&state);
        assert!(desc.contains("Perfil: Por defecto"));
        assert!(desc.contains("DPI: 800 DPI"));
    }

    #[test]
    fn test_menu_structure() {
        let cached = TrayState {
            enabled: true,
            active_target_name: Some("Gaming".to_string()),
            current_dpi: Some(1200),
            active_exe: None,
            battery_percentage: None,
        };
        let tray = CheddarTray::new(cached);

        let menu = tray.menu();
        // 1. Abrir Cheddar, 2. Cerrar Cheddar, 3. Separator, 4. Perfil, 5. DPI = 5 items
        assert_eq!(menu.len(), 5);
        assert_eq!(tray.id(), "io.github.rilorca.Cheddar");
        assert_eq!(tray.title(), "Cheddar");
        assert_eq!(tray.icon_name(), "io.github.rilorca.Cheddar-symbolic");
    }
}
