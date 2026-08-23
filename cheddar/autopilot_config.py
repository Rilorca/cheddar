# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilot_config.py — part of Cheddar AutoPilot fork
# Persists game→profile rules to ~/.config/cheddar/autopilot.json

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.expanduser("~/.config/cheddar")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "autopilot.json")

# One-time migration: this app used to be called Piper AutoPilot and stored
# its settings under ~/.config/piper. Carry an existing config over so a
# rename doesn't lose the user's rules, saved profiles and backups.
_LEGACY_DIR = os.path.expanduser("~/.config/piper")


def _migrate_legacy_config() -> None:
    if os.path.isdir(_CONFIG_DIR) or not os.path.isdir(_LEGACY_DIR):
        return
    try:
        import shutil

        shutil.copytree(_LEGACY_DIR, _CONFIG_DIR)
        logger.info("migrated settings from %s to %s", _LEGACY_DIR, _CONFIG_DIR)
    except OSError as e:
        logger.warning("could not migrate legacy config: %s", e)


_migrate_legacy_config()

_DEFAULTS: Dict[str, Any] = {
    "enabled": False,
    "default_profile": 0,
    "rules": {},  # { "executable": profile_index }
}


def load() -> Dict[str, Any]:
    if not os.path.exists(_CONFIG_FILE):
        return dict(_DEFAULTS)
    try:
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    except Exception as e:
        logger.warning("autopilot: could not load config (%s) — using defaults", e)
        return dict(_DEFAULTS)


def save(config: Dict[str, Any]) -> None:
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("autopilot: could not save config: %s", e)
