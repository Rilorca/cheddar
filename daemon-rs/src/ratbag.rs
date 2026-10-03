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

        let _res: u32 = proxy.call("SetActive", &()).await?;
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

        let _res: u32 = proxy.call("Commit", &()).await?;
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

    pub async fn get_resolutions(&self, profile_path: &OwnedObjectPath) -> Result<Vec<OwnedObjectPath>> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            profile_path,
            RATBAG_PROFILE_IFACE,
        )
        .await?;

        let res: Vec<OwnedObjectPath> = proxy.get_property("Resolutions").await?;
        Ok(res)
    }

    pub async fn get_buttons(&self, profile_path: &OwnedObjectPath) -> Result<Vec<OwnedObjectPath>> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            profile_path,
            RATBAG_PROFILE_IFACE,
        )
        .await?;

        let btns: Vec<OwnedObjectPath> = proxy.get_property("Buttons").await?;
        Ok(btns)
    }

    pub async fn get_leds(&self, profile_path: &OwnedObjectPath) -> Result<Vec<OwnedObjectPath>> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            profile_path,
            RATBAG_PROFILE_IFACE,
        )
        .await?;

        let leds: Vec<OwnedObjectPath> = proxy.get_property("Leds").await?;
        Ok(leds)
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

        // 3. Resolutions
        if let Some(res_list) = data.get("resolutions").and_then(|v| v.as_array()) {
            if let Ok(res_paths) = self.get_resolutions(profile_path).await {
                for (i, res_path) in res_paths.iter().enumerate() {
                    if let Some(res_obj) = res_list.get(i) {
                        let res_proxy = zbus::Proxy::new(
                            &self.conn,
                            RATBAG_DEST,
                            res_path,
                            DBUS_PROPERTIES_IFACE,
                        )
                        .await?;

                        if let Some(dpi) = res_obj.get("dpi").and_then(|v| v.as_u64()) {
                            let _: Result<()> = res_proxy
                                .call(
                                    "Set",
                                    &(
                                        "org.freedesktop.ratbag1.Resolution",
                                        "Resolution",
                                        Value::new(Value::new(dpi as u32)),
                                    ),
                                )
                                .await;
                        }

                        if res_obj.get("active").and_then(|v| v.as_bool()).unwrap_or(false) {
                            let r_proxy = zbus::Proxy::new(
                                &self.conn,
                                RATBAG_DEST,
                                res_path,
                                "org.freedesktop.ratbag1.Resolution",
                            )
                            .await?;
                            let _res: u32 = r_proxy.call("SetActive", &()).await?;
                        }
                    }
                }
            }
        }

        // 4. Buttons
        if let Some(btn_list) = data.get("buttons").and_then(|v| v.as_array()) {
            if let Ok(btn_paths) = self.get_buttons(profile_path).await {
                for (i, btn_path) in btn_paths.iter().enumerate() {
                    if let Some(btn_obj) = btn_list.get(i) {
                        let btn_proxy = zbus::Proxy::new(
                            &self.conn,
                            RATBAG_DEST,
                            btn_path,
                            DBUS_PROPERTIES_IFACE,
                        )
                        .await?;

                        let action_type = btn_obj.get("type").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
                        if action_type == 0 {
                            // ActionType.NONE (disable)
                            let _: Result<()> = btn_proxy
                                .call(
                                    "Set",
                                    &(
                                        "org.freedesktop.ratbag1.Button",
                                        "Mapping",
                                        Value::new((0u32, Value::new(0u32))),
                                    ),
                                )
                                .await;
                        } else if action_type == 1 {
                            // ActionType.BUTTON
                            if let Some(val) = btn_obj.get("value").and_then(|v| v.as_u64()) {
                                let _: Result<()> = btn_proxy
                                    .call(
                                        "Set",
                                        &(
                                            "org.freedesktop.ratbag1.Button",
                                            "Mapping",
                                            Value::new((1u32, Value::new(val as u32))),
                                        ),
                                    )
                                    .await;
                            }
                        } else if action_type == 2 {
                            // ActionType.SPECIAL
                            if let Some(val) = btn_obj.get("value").and_then(|v| v.as_u64()) {
                                let _: Result<()> = btn_proxy
                                    .call(
                                        "Set",
                                        &(
                                            "org.freedesktop.ratbag1.Button",
                                            "Mapping",
                                            Value::new((2u32, Value::new(val as u32))),
                                        ),
                                    )
                                    .await;
                            }
                        } else if action_type == 3 {
                            // ActionType.KEY
                            if let Some(val) = btn_obj.get("value").and_then(|v| v.as_u64()) {
                                let _: Result<()> = btn_proxy
                                    .call(
                                        "Set",
                                        &(
                                            "org.freedesktop.ratbag1.Button",
                                            "Mapping",
                                            Value::new((3u32, Value::new(val as u32))),
                                        ),
                                    )
                                    .await;
                            }
                        }
                    }
                }
            }
        }

        // 5. LEDs
        if let Some(led_list) = data.get("leds").and_then(|v| v.as_array()) {
            if let Ok(led_paths) = self.get_leds(profile_path).await {
                for (i, led_path) in led_paths.iter().enumerate() {
                    if let Some(led_obj) = led_list.get(i) {
                        let led_proxy = zbus::Proxy::new(
                            &self.conn,
                            RATBAG_DEST,
                            led_path,
                            DBUS_PROPERTIES_IFACE,
                        )
                        .await?;

                        if let Some(mode) = led_obj.get("mode").and_then(|v| v.as_u64()) {
                            let _: Result<()> = led_proxy
                                .call(
                                    "Set",
                                    &(
                                        "org.freedesktop.ratbag1.Led",
                                        "Mode",
                                        Value::new(mode as u32),
                                    ),
                                )
                                .await;
                        }

                        if let Some(color_arr) = led_obj.get("color").and_then(|v| v.as_array()) {
                            if color_arr.len() == 3 {
                                let r = color_arr[0].as_u64().unwrap_or(0) as u32;
                                let g = color_arr[1].as_u64().unwrap_or(0) as u32;
                                let b = color_arr[2].as_u64().unwrap_or(0) as u32;
                                let _: Result<()> = led_proxy
                                    .call(
                                        "Set",
                                        &(
                                            "org.freedesktop.ratbag1.Led",
                                            "Color",
                                            Value::new((r, g, b)),
                                        ),
                                    )
                                    .await;
                            }
                        }
                    }
                }
            }
        }

        Ok(())
    }
}

fn extract_u32(val: &Value) -> Option<u32> {
    let mut current = val;
    while let Value::Value(inner) = current {
        current = inner.as_ref();
    }
    match current {
        Value::U32(v) => Some(*v),
        Value::I32(v) if *v > 0 => Some(*v as u32),
        Value::U64(v) => Some(*v as u32),
        Value::I64(v) if *v > 0 => Some(*v as u32),
        Value::U16(v) => Some(*v as u32),
        Value::I16(v) if *v > 0 => Some(*v as u32),
        _ => None,
    }
}

/// Reads the live hardware active profile & resolution slot directly from the Logitech G600 HID feature report (0xF0)
fn read_g600_hw_slot() -> Option<(u32, u32)> {
    use std::fs::OpenOptions;
    use std::os::unix::io::AsRawFd;

    // Search for Logitech G600 hidraw interface (if01 / configuration interface)
    let candidates = [
        "/dev/input/by-id/usb-Logitech_Gaming_Mouse_G600_485A504665A70017-if01-hidraw",
        "/dev/hidraw1",
        "/dev/hidraw0",
    ];

    for path in &candidates {
        if let Ok(file) = OpenOptions::new().read(true).write(true).open(path) {
            let mut buf: [u8; 4] = [0xF0, 0, 0, 0];
            // Linux HIDIOCGFEATURE(4): _IOC(_IOC_WRITE|_IOC_READ, 'H', 0x07, 4) = 0xC0044807
            const HIDIOCGFEATURE_4: u64 = 0xC0044807;
            unsafe {
                extern "C" {
                    fn ioctl(fd: i32, request: u64, ...) -> i32;
                }
                let res = ioctl(file.as_raw_fd(), HIDIOCGFEATURE_4, buf.as_mut_ptr());
                if res >= 0 && buf[0] == 0xF0 {
                    let b1 = buf[1];
                    let res_idx = ((b1 >> 1) & 0x03) as u32;
                    let prof_idx = ((b1 >> 4) & 0x0F) as u32;
                    return Some((prof_idx, res_idx));
                }
            }
        }
    }
    None
}

impl RatbagClient {
    /// Read the currently active DPI for the active profile
    pub async fn get_active_dpi(&self, device_path: &OwnedObjectPath) -> Result<Option<u32>> {
        let hw_slot = read_g600_hw_slot();

        let profiles = self.get_profile_paths(device_path).await?;
        for p_path in profiles {
            let p_proxy = zbus::Proxy::new(
                &self.conn,
                RATBAG_DEST,
                &p_path,
                RATBAG_PROFILE_IFACE,
            )
            .await?;

            let p_index: u32 = p_proxy.get_property("Index").await.unwrap_or(0);
            let p_is_active: bool = if let Some((hw_prof, _)) = hw_slot {
                hw_prof == p_index
            } else {
                p_proxy.get_property("IsActive").await.unwrap_or(false)
            };

            if p_is_active {
                let res_paths = self.get_resolutions(&p_path).await?;
                for r_path in res_paths {
                    let r_proxy = zbus::Proxy::new(
                        &self.conn,
                        RATBAG_DEST,
                        &r_path,
                        "org.freedesktop.ratbag1.Resolution",
                    )
                    .await?;

                    let r_index: u32 = r_proxy.get_property("Index").await.unwrap_or(0);
                    let r_active: bool = if let Some((_, hw_res)) = hw_slot {
                        hw_res == r_index
                    } else {
                        r_proxy.get_property("IsActive").await.unwrap_or(false)
                    };

                    if r_active {
                        let res_val: Value = r_proxy.get_property("Resolution").await?;
                        if let Some(dpi) = extract_u32(&res_val) {
                            return Ok(Some(dpi));
                        }
                    }
                }
            }
        }
        Ok(None)
    }

    /// Read battery percentage if supported by the ratbag device (or UPower)
    pub async fn get_battery(&self, device_path: &OwnedObjectPath) -> Result<Option<u32>> {
        let proxy = zbus::Proxy::new(
            &self.conn,
            RATBAG_DEST,
            device_path,
            RATBAG_DEVICE_IFACE,
        )
        .await?;

        // Try ratbagd Battery property (available on wireless devices)
        if let Ok(val) = proxy.get_property::<Value>("Battery").await {
            if let Some(pct) = extract_u32(&val) {
                return Ok(Some(pct));
            }
        }
        Ok(None)
    }
}

