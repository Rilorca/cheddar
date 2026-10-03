use std::collections::HashMap;
use std::sync::Arc;
use zbus::Connection;
use zbus::zvariant::Value;
use log::{info, warn};

pub struct Notifier {
    session_conn: Option<Arc<Connection>>,
    last_notify_id: tokio::sync::Mutex<u32>,
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
        Self {
            session_conn,
            last_notify_id: tokio::sync::Mutex::new(0),
        }
    }

    /// Check if the desktop notifications server is currently inhibited (e.g. fullscreen game or DND)
    pub async fn is_inhibited(&self) -> bool {
        if let Some(conn) = &self.session_conn {
            let proxy_res = zbus::Proxy::new(
                conn,
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications",
            )
            .await;

            if let Ok(proxy) = proxy_res {
                return proxy.get_property("Inhibited").await.unwrap_or(false);
            }
        }
        false
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
            let mut hints: HashMap<&str, Value> = HashMap::new();

            // When desktop is Inhibited (fullscreen game / DND), use urgency 2 to break through.
            // Otherwise use urgency 1 so it appears as a smooth standard toast that auto-dismisses.
            let is_inhibited = self.is_inhibited().await;
            let urgency_val: u8 = if is_inhibited { 2 } else { 1 };
            hints.insert("urgency", Value::U8(urgency_val));
            hints.insert("transient", Value::Bool(true));
            hints.insert("desktop-entry", Value::from("io.github.rilorca.Cheddar"));
            hints.insert("category", Value::from("device"));

            let replaces_id = {
                let id_guard = self.last_notify_id.lock().await;
                *id_guard
            };

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
                                replaces_id,
                                icon,
                                summary,
                                body,
                                &actions,
                                &hints,
                                timeout_ms,
                            ),
                        )
                        .await;

                    match res {
                        Ok(id) => {
                            let mut id_guard = self.last_notify_id.lock().await;
                            *id_guard = id;
                            info!("Sent notification id {}: '{} - {}'", id, summary, body);
                        }
                        Err(e) => warn!("notifier: D-Bus notify call failed: {}", e),
                    }
                }
                Err(e) => {
                    warn!("notifier: could not create notification proxy: {}", e);
                }
            }
        } else {
            warn!("notifier: no session D-Bus connection available");
        }
    }
}
