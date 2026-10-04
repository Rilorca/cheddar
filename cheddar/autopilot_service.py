# SPDX-License-Identifier: GPL-2.0-or-later

"""autopilot_service.py — coordination between Cheddar GUI and native Rust daemon.

Detects whether `cheddar-autopilot.service` is running via systemd --user so
that Cheddar GUI does not spawn duplicate Python watcher threads or redundant
system tray icons.
"""

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

SERVICE_NAME = "cheddar-autopilot.service"


def is_daemon_service_active() -> bool:
    """Check if the native Rust daemon is currently running via systemd."""
    if not shutil.which("systemctl"):
        return False
    try:
        res = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.0,
        )
        return res.returncode == 0 and res.stdout.strip() == "active"
    except Exception as exc:
        logger.debug("Failed to check %s status: %s", SERVICE_NAME, exc)
        return False


def ensure_daemon_service_running() -> bool:
    """Ensure the native Rust daemon service is started and active."""
    if is_daemon_service_active():
        return True
    if start_daemon_service():
        return is_daemon_service_active()
    return False


def is_daemon_service_enabled() -> bool:
    """Check if the native Rust daemon is enabled to start on login."""
    if not shutil.which("systemctl"):
        return False
    try:
        res = subprocess.run(
            ["systemctl", "--user", "is-enabled", SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.0,
        )
        return res.returncode == 0 and res.stdout.strip() == "enabled"
    except Exception:
        return False


def start_daemon_service() -> bool:
    """Start the user systemd service."""
    if not shutil.which("systemctl"):
        return False
    try:
        res = subprocess.run(
            ["systemctl", "--user", "start", SERVICE_NAME],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3.0,
        )
        return res.returncode == 0
    except Exception as exc:
        logger.warning("Failed to start %s: %s", SERVICE_NAME, exc)
        return False


def stop_daemon_service() -> bool:
    """Stop the user systemd service."""
    if not shutil.which("systemctl"):
        return False
    try:
        res = subprocess.run(
            ["systemctl", "--user", "stop", SERVICE_NAME],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3.0,
        )
        return res.returncode == 0
    except Exception as exc:
        logger.warning("Failed to stop %s: %s", SERVICE_NAME, exc)
        return False
