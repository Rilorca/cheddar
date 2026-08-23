# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilot_daemon.py — part of Piper AutoPilot fork
#
# Headless AutoPilot: runs the game watcher against ratbagd without the GUI,
# so profiles keep switching while Piper is closed — the same role G HUB's
# background service plays on Windows.
#
# Usage:
#     python3 -m piper.autopilot_daemon [-v]
#
# Reads the same config the GUI writes (~/.config/piper/autopilot.json) and
# reloads it automatically when the GUI saves changes, so rules edited in the
# AutoPilot tab apply live. Profile switches are idempotent in ratbagd, so
# running the daemon alongside the GUI is harmless.

import argparse
import logging
import signal
import sys

from gi.repository import Gio, GLib

from . import autopilot_profiles as ap
from .autopilot_config import _CONFIG_FILE, load as cfg_load
from .autopilot_watcher import AutoPilotWatcher, RuleTarget
from .ratbagd import Ratbagd, RatbagdIncompatibleError, RatbagdUnavailableError

RATBAGD_API_VERSION = 2

logger = logging.getLogger("piper.autopilot")


class AutoPilotDaemon:
    def __init__(self) -> None:
        try:
            self._ratbag = Ratbagd(RATBAGD_API_VERSION)
        except RatbagdUnavailableError:
            sys.exit("ratbagd is not running (try: systemctl start ratbagd)")
        except RatbagdIncompatibleError as e:
            sys.exit(
                f"incompatible ratbagd API (need {e.required_version}, "
                f"got {e.ratbagd_version})"
            )

        if not self._ratbag.devices:
            logger.warning("no devices yet — will pick them up when plugged in")
        for device in self._ratbag.devices:
            logger.info("device: %s", device.name)

        self._config = cfg_load()
        config = self._config
        self._watcher = AutoPilotWatcher(
            rules=self._effective_rules(),
            on_switch=self._on_switch,
            default_profile=config.get("default_profile", 0),
        )

        # Reload rules whenever the GUI (or the user) rewrites the config.
        self._monitor = Gio.File.new_for_path(_CONFIG_FILE).monitor_file(
            Gio.FileMonitorFlags.NONE, None
        )
        self._monitor.connect("changed", self._on_config_changed)

        self._watcher.start()
        if not config.get("enabled", False):
            logger.info("AutoPilot is disabled in the config — paused")
        logger.info(
            "watching for games (%d rule(s), default profile %d)",
            len(self._effective_rules()),
            config.get("default_profile", 0),
        )

    def _effective_rules(self) -> dict:
        """The rules to act on: none while the user has AutoPilot disabled.

        The GUI toggle only stops the GUI's own watcher; this daemon must
        honor the same `enabled` flag or switching keeps happening with the
        toggle off. An empty rule set makes the watcher's tick a no-op, so
        toggling re-enables instantly via the config file monitor without
        restarting the thread.
        """
        if not self._config.get("enabled", False):
            return {}
        return self._config.get("rules", {})

    def _on_config_changed(self, _monitor, _file, _other, event) -> None:
        if event not in (
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
        ):
            return
        self._config = cfg_load()
        config = self._config
        self._watcher.update_rules(
            self._effective_rules(), config.get("default_profile", 0)
        )
        logger.info(
            "config reloaded (%d rule(s)%s)",
            len(self._effective_rules()),
            "" if config.get("enabled", False) else ", AutoPilot disabled — paused",
        )

    def _on_switch(self, target: RuleTarget, exe_name: str) -> None:
        # Called from the watcher thread; hop onto the main loop for D-Bus.
        GLib.idle_add(self._switch_main_thread, target, exe_name)

    def _switch_main_thread(self, target: RuleTarget, exe_name: str) -> bool:
        for device in self._ratbag.devices:
            try:
                ap.activate_target(device, target, self._config)
                logger.info("%s: '%s' -> %s", device.name, exe_name, target)
            except Exception as exc:
                logger.error("switch failed on %s: %s", device.name, exc)
        return False  # one-shot

    def stop(self) -> None:
        self._watcher.request_stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Piper AutoPilot daemon: switch mouse profiles per game, headless"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    daemon = AutoPilotDaemon()
    loop = GLib.MainLoop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        GLib.unix_signal_add(GLib.PRIORITY_HIGH, sig, lambda *_: loop.quit())
    try:
        loop.run()
    finally:
        daemon.stop()
        logger.info("bye")


if __name__ == "__main__":
    main()
