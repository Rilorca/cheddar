# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

AUTOSTART_FILENAME = "io.github.rilorca.Cheddar.desktop"
LEGACY_FILENAME = "cheddar.desktop"


def _get_autostart_dir() -> str:
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(config_home, "autostart")


def _get_autostart_path() -> str:
    return os.path.join(_get_autostart_dir(), AUTOSTART_FILENAME)


def _get_legacy_path() -> str:
    return os.path.join(_get_autostart_dir(), LEGACY_FILENAME)


def is_flatpak() -> bool:
    return os.path.exists("/.flatpak-info")


def is_autostart_enabled() -> bool:
    """Check whether Cheddar is configured to launch on desktop startup."""
    for path in (_get_autostart_path(), _get_legacy_path()):
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "X-GNOME-Autostart-enabled=false" in content or "Hidden=true" in content:
                    return False
                return True
            except OSError as e:
                logger.warning("Failed to read autostart file %s: %s", path, e)
    return False


def set_autostart_enabled(enabled: bool) -> bool:
    """Enable or disable Cheddar launching on desktop login."""
    target_path = _get_autostart_path()
    legacy_path = _get_legacy_path()

    if not enabled:
        for path in (target_path, legacy_path):
            if os.path.isfile(path):
                try:
                    os.remove(path)
                    logger.info("Removed autostart file: %s", path)
                except OSError as e:
                    logger.warning("Failed to remove autostart file %s: %s", path, e)
                    return False
        return True

    # Enable autostart
    autostart_dir = _get_autostart_dir()
    try:
        os.makedirs(autostart_dir, exist_ok=True)
    except OSError as e:
        logger.error("Failed to create autostart directory %s: %s", autostart_dir, e)
        return False

    exec_cmd = "flatpak run io.github.rilorca.Cheddar --background" if is_flatpak() else "cheddar --background"

    desktop_entry = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Cheddar\n"
        "GenericName=Mouse AutoPilot\n"
        "Comment=Configurable mouse utility with AutoPilot per-game profile switcher\n"
        f"Exec={exec_cmd}\n"
        "Icon=io.github.rilorca.Cheddar\n"
        "Terminal=false\n"
        "Categories=GTK;GNOME;Utility;\n"
        "StartupNotify=false\n"
        "X-GNOME-Autostart-enabled=true\n"
        "X-KDE-autostart-after=panel\n"
    )

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(desktop_entry)
        logger.info("Created autostart entry: %s", target_path)
        return True
    except OSError as e:
        logger.error("Failed to write autostart entry %s: %s", target_path, e)
        return False
