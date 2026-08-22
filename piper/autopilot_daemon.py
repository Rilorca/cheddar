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

from .autopilot_config import _CONFIG_FILE, load as cfg_load
from .autopilot_watcher import AutoPilotWatcher
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

        config = cfg_load()
        self._watcher = AutoPilotWatcher(
            rules=config.get("rules", {}),
            on_switch=self._on_switch,
            default_profile=config.get("default_profile", 0),
        )

        # Reload rules whenever the GUI (or the user) rewrites the config.
        self._monitor = Gio.File.new_for_path(_CONFIG_FILE).monitor_file(
            Gio.FileMonitorFlags.NONE, None
        )
        self._monitor.connect("changed", self._on_config_changed)

        self._watcher.start()
        logger.info(
            "watching for games (%d rule(s), default profile %d)",
            len(config.get("rules", {})),
            config.get("default_profile", 0),
        )

    def _on_config_changed(self, _monitor, _file, _other, event) -> None:
        if event not in (
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
        ):
            return
        config = cfg_load()
        self._watcher.update_rules(
            config.get("rules", {}), config.get("default_profile", 0)
        )
        logger.info("config reloaded (%d rule(s))", len(config.get("rules", {})))

    def _on_switch(self, profile_index: int, exe_name: str) -> None:
        # Called from the watcher thread; hop onto the main loop for D-Bus.
        GLib.idle_add(self._switch_main_thread, profile_index, exe_name)

    def _switch_main_thread(self, profile_index: int, exe_name: str) -> bool:
        for device in self._ratbag.devices:
            for profile in device.profiles:
                if profile.index == profile_index:
                    try:
                        profile.set_active()
                        device.commit()
                        logger.info(
                            "%s: '%s' -> profile %d",
                            device.name,
                            exe_name,
                            profile_index,
                        )
                    except Exception as exc:
                        logger.error("switch failed on %s: %s", device.name, exc)
                    break
            else:
                logger.warning(
                    "%s has no profile %d — rule ignored", device.name, profile_index
                )
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
