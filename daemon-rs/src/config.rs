use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use log::warn;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum RuleTarget {
    Index(u32),
    Software(String),
}

impl std::fmt::Display for RuleTarget {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RuleTarget::Index(idx) => write!(f, "{}", idx),
            RuleTarget::Software(name) => write!(f, "{}", name),
        }
    }
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoPilotConfig {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub default_profile: u32,
    #[serde(default)]
    pub rules: HashMap<String, RuleTarget>,
    #[serde(default)]
    pub scratch_slot: Option<u32>,
    #[serde(default = "default_true")]
    pub notifications_enabled: bool,
}

impl Default for AutoPilotConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            default_profile: 0,
            rules: HashMap::new(),
            scratch_slot: None,
            notifications_enabled: true,
        }
    }
}

pub fn config_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("~/.config"))
        .join("cheddar")
        .join("autopilot.json")
}

pub fn state_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("~/.config"))
        .join("cheddar")
        .join("autopilot_state.json")
}

pub fn software_profiles_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("~/.config"))
        .join("cheddar")
        .join("autopilot_profiles.json")
}

pub fn load_config() -> AutoPilotConfig {
    let path = config_path();
    if !path.exists() {
        return AutoPilotConfig::default();
    }

    match fs::read_to_string(&path) {
        Ok(content) => match serde_json::from_str::<AutoPilotConfig>(&content) {
            Ok(cfg) => cfg,
            Err(e) => {
                warn!("autopilot: failed to parse config ({}): using defaults", e);
                AutoPilotConfig::default()
            }
        },
        Err(e) => {
            warn!("autopilot: could not read config ({}): using defaults", e);
            AutoPilotConfig::default()
        }
    }
}

pub fn update_active_user_profile(profile_name: Option<&str>) {
    let path = state_path();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let payload = match profile_name {
        Some(name) => serde_json::json!({ "active_user_profile": name }),
        None => serde_json::json!({ "active_user_profile": null }),
    };

    if let Ok(json_str) = serde_json::to_string_pretty(&payload) {
        let _ = fs::write(path, json_str);
    }
}

pub fn save_config(cfg: &AutoPilotConfig) -> Result<(), std::io::Error> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let json_str = serde_json::to_string_pretty(cfg)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
    fs::write(path, json_str)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_default_and_deserialize() {
        let json_data = r#"{
            "enabled": true,
            "default_profile": 1,
            "rules": {
                "heroes of the storm.exe": 2,
                "overwatch.exe": "sw:Overwatch"
            }
        }"#;

        let cfg: AutoPilotConfig = serde_json::from_str(json_data).expect("valid json");
        assert!(cfg.enabled);
        assert_eq!(cfg.default_profile, 1);
        assert_eq!(cfg.rules.get("heroes of the storm.exe"), Some(&RuleTarget::Index(2)));
        assert_eq!(cfg.rules.get("overwatch.exe"), Some(&RuleTarget::Software("sw:Overwatch".to_string())));
    }

    #[test]
    fn test_rule_target_display() {
        let t1 = RuleTarget::Index(0);
        assert_eq!(t1.to_string(), "0");

        let t2 = RuleTarget::Software("sw:Mobas".to_string());
        assert_eq!(t2.to_string(), "sw:Mobas");
    }

    #[test]
    fn test_config_with_scratch_slot() {
        let json_data = r#"{
            "enabled": true,
            "default_profile": 0,
            "scratch_slot": 4,
            "rules": {}
        }"#;

        let cfg: AutoPilotConfig = serde_json::from_str(json_data).expect("valid json");
        assert_eq!(cfg.scratch_slot, Some(4));
    }

    #[test]
    fn test_config_empty_json() {
        let cfg: AutoPilotConfig = serde_json::from_str("{}").expect("valid empty json");
        assert!(!cfg.enabled);
        assert_eq!(cfg.default_profile, 0);
        assert!(cfg.rules.is_empty());
        assert_eq!(cfg.scratch_slot, None);
        assert!(cfg.notifications_enabled);
    }

    #[test]
    fn test_config_notifications_disabled() {
        let json_data = r#"{"notifications_enabled": false}"#;
        let cfg: AutoPilotConfig = serde_json::from_str(json_data).expect("valid json");
        assert!(!cfg.notifications_enabled);
    }
}

