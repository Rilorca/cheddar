# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilot_config.py — part of Piper AutoPilot fork
# Persists game→profile rules to ~/.config/piper/autopilot.json

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.expanduser("~/.config/piper")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "autopilot.json")

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
