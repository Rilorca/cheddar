use std::collections::HashMap;
use std::sync::Arc;
use zbus::Connection;
use zbus::zvariant::Value;
use log::{debug, warn};

pub struct Notifier {
    session_conn: Option<Arc<Connection>>,
}

impl Notifier {
    pub async fn new() -> Self {
        let session_conn = match Connection::session().await {
            Ok(conn) => Some(Arc::new(conn)),
            Err(e) => {
                warn!("notifier: could not connect to session D-Bus: {}", e);
                None
            }
        };
        Self { session_conn }
    }

    /// Check if the screensaver/screen lock is currently active
    pub async fn is_screen_saver_active(&self) -> bool {
        if let Some(conn) = &self.session_conn {
            let proxy_res = zbus::Proxy::new(
                conn,
                "org.freedesktop.ScreenSaver",
                "/ScreenSaver",
                "org.freedesktop.ScreenSaver",
            )
            .await;

            if let Ok(proxy) = proxy_res {
                let res: zbus::Result<bool> = proxy.call("GetActive", &()).await;
                if let Ok(active) = res {
                    return active;
                }
            }
        }
        false
    }

    /// Send a desktop notification via org.freedesktop.Notifications
    pub async fn notify(&self, summary: &str, body: &str, icon: &str, timeout_ms: i32) {
        if let Some(conn) = &self.session_conn {
            let actions: Vec<String> = Vec::new();
            let hints: HashMap<String, Value> = HashMap::new();

            let proxy_res = zbus::Proxy::new(
                conn,
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications",
            )
            .await;

            match proxy_res {
                Ok(proxy) => {
                    let res: zbus::Result<u32> = proxy
                        .call(
                            "Notify",
                            &(
                                "Cheddar AutoPilot",
                                0u32,
                                icon,
                                summary,
                                body,
                                &actions,
                                &hints,
                                timeout_ms,
                            ),
                        )
                        .await;

                    if let Err(e) = res {
                        debug!("notifier: D-Bus notify call failed: {}", e);
                    }
                }
                Err(e) => {
                    debug!("notifier: could not create notification proxy: {}", e);
                }
            }
        }
    }
}
