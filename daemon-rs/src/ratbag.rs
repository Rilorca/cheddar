use std::collections::HashMap;
use std::fs;
use zbus::zvariant::{OwnedObjectPath, Value};
use zbus::{Connection, Result};
use log::{debug, info, warn};

use crate::config::{software_profiles_path, update_active_user_profile, AutoPilotConfig, RuleTarget};

const RATBAG_DEST: &str = "org.freedesktop.ratbag1";
const RATBAG_PATH: &str = "/org/freedesktop/ratbag1";
const RATBAG_MANAGER_IFACE: &str = "org.freedesktop.ratbag1.Manager";
const RATBAG_DEVICE_IFACE: &str = "org.freedesktop.ratbag1.Device";
const RATBAG_PROFILE_IFACE: &str = "org.freedesktop.ratbag1.Profile";
const DBUS_PROPERTIES_IFACE: &str = "org.freedesktop.DBus.Properties";

pub struct RatbagClient {
    conn: Connection,
}

impl RatbagClient {
    pub async fn connect() -> Result<Self> {
        let conn = Connection::system().await?;
        Ok(Self { conn })
    }

    pub async fn list_device_paths(&self) -> Result<Vec<OwnedObjectPath>> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            RATBAG_PATH,
            RATBAG_MANAGER_IFACE,
        )
        .await?;

        let devices: Vec<OwnedObjectPath> = proxy.get_property("Devices").await?;
        Ok(devices)
    }

    pub async fn get_device_name(&self, device_path: &OwnedObjectPath) -> Result<String> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            device_path,
            RATBAG_DEVICE_IFACE,
        )
        .await?;

        let name: String = proxy.get_property("Name").await?;
        Ok(name)
    }

    pub async fn get_profile_paths(&self, device_path: &OwnedObjectPath) -> Result<Vec<OwnedObjectPath>> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            device_path,
            RATBAG_DEVICE_IFACE,
        )
        .await?;

        let profiles: Vec<OwnedObjectPath> = proxy.get_property("Profiles").await?;
        Ok(profiles)
    }

    pub async fn get_profile_index(&self, profile_path: &OwnedObjectPath) -> Result<u32> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            profile_path,
            RATBAG_PROFILE_IFACE,
        )
        .await?;

        let index: u32 = proxy.get_property("Index").await?;
        Ok(index)
    }

    pub async fn set_profile_active(&self, profile_path: &OwnedObjectPath) -> Result<()> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            profile_path,
            RATBAG_PROFILE_IFACE,
        )
        .await?;

        let () = proxy.call("SetActive", &()).await?;
        Ok(())
    }

    pub async fn commit_device(&self, device_path: &OwnedObjectPath) -> Result<()> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            device_path,
            RATBAG_DEVICE_IFACE,
        )
        .await?;

        let () = proxy.call("Commit", &()).await?;
        Ok(())
    }

    pub async fn activate_target(
        &self,
        device_path: &OwnedObjectPath,
        target: &RuleTarget,
        config: &AutoPilotConfig,
    ) -> Result<()> {
        let profiles = self.get_profile_paths(device_path).await?;
        if profiles.is_empty() {
            warn!("Device {:?} has no profiles", device_path);
            return Ok(());
        }

        match target {
            RuleTarget::Index(target_idx) => {
                for p_path in &profiles {
                    if let Ok(idx) = self.get_profile_index(p_path).await {
                        if idx == *target_idx {
                            self.set_profile_active(p_path).await?;
                            self.commit_device(device_path).await?;
                            update_active_user_profile(None);
                            debug!("Activated onboard profile {} on {:?}", target_idx, device_path);
                            return Ok(());
                        }
                    }
                }
                warn!("Profile index {} not found on device {:?}", target_idx, device_path);
            }
            RuleTarget::Software(sw_name) => {
                let clean_name = sw_name.strip_prefix("sw:").unwrap_or(sw_name);
                let store_path = software_profiles_path();
                let store_content = fs::read_to_string(&store_path).unwrap_or_default();
                let store: HashMap<String, serde_json::Value> =
                    serde_json::from_str(&store_content).unwrap_or_default();

                if let Some(profile_data) = store.get(clean_name) {
                    let total_profiles = profiles.len() as u32;
                    let scratch_slot = config.scratch_slot.unwrap_or(total_profiles.saturating_sub(1));

                    for p_path in &profiles {
                        if let Ok(idx) = self.get_profile_index(p_path).await {
                            if idx == scratch_slot {
                                self.apply_software_profile(p_path, profile_data).await?;
                                self.set_profile_active(p_path).await?;
                                self.commit_device(device_path).await?;
                                update_active_user_profile(Some(clean_name));
                                info!("Activated software profile '{}' on slot {}", clean_name, scratch_slot);
                                return Ok(());
                            }
                        }
                    }
                    warn!("Scratch slot {} not found on device {:?}", scratch_slot, device_path);
                } else {
                    warn!("Software profile '{}' does not exist in store", clean_name);
                }
            }
        }

        Ok(())
    }

    async fn apply_software_profile(
        &self,
        profile_path: &OwnedObjectPath,
        data: &serde_json::Value,
    ) -> Result<()> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            profile_path,
            DBUS_PROPERTIES_IFACE,
        )
        .await?;

        // 1. Report Rate
        if let Some(report_rate) = data.get("report_rate").and_then(|v| v.as_u64()) {
            let () = proxy
                .call(
                    "Set",
                    &(
                        RATBAG_PROFILE_IFACE,
                        "ReportRate",
                        Value::new(report_rate as u32),
                    ),
                )
                .await?;
        }

        // 2. Name
        if let Some(name) = data.get("name").and_then(|v| v.as_str()) {
            let _: Result<()> = proxy
                .call(
                    "Set",
                    &(RATBAG_PROFILE_IFACE, "Name", Value::new(name)),
                )
                .await;
        }

        Ok(())
    }
}
