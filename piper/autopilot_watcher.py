# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilot_watcher.py — part of Piper AutoPilot fork
# Polls /proc every POLL_INTERVAL seconds to detect running game executables
# and fires callbacks to switch ratbagd profiles accordingly.

import os
import threading
import logging
from typing import Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)

POLL_INTERVAL = 2.0  # seconds


def _add_name(exes: Set[str], name: str) -> None:
    """Add a lowercase executable name, plus an alias without its .exe
    extension so rules match whether or not the user typed the extension."""
    name = name.lower()
    if not name:
        return
    exes.add(name)
    if name.endswith(".exe"):
        exes.add(name[:-4])


def _basename_any_os(path: str) -> str:
    """Basename that also understands Windows-style paths, as found in the
    cmdline of Wine/Proton processes (e.g. 'Z:\\Games\\Foo\\foo.exe')."""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _running_executables() -> Set[str]:
    """Return lowercase basenames of every executable visible in /proc.

    Two sources per process:
      • /proc/PID/exe      — native Linux binaries.
      • /proc/PID/cmdline  — argv[0]. For Wine/Proton games /proc/PID/exe
        points at the wine preloader, not the game; the game's Windows path
        lives in argv[0], so this is what makes Steam/Proton, Lutris and
        Heroic titles detectable.

    Each name is also added without its .exe extension ("extension optional"
    as promised by the rule dialog). Only argv[0] is inspected — scanning
    every argument would false-positive on e.g. 'grep game.exe'.
    """
    exes: Set[str] = set()
    try:
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit():
                continue
            try:
                exe_path = os.readlink(f"/proc/{entry.name}/exe")
                _add_name(exes, os.path.basename(exe_path))
            except OSError:
                pass
            try:
                with open(f"/proc/{entry.name}/cmdline", "rb") as f:
                    argv0 = f.read(4096).split(b"\0", 1)[0]
                if argv0:
                    _add_name(exes, _basename_any_os(argv0.decode("utf-8", "replace")))
            except OSError:
                pass
    except Exception as e:
        logger.debug("Error scanning /proc: %s", e)
    return exes


class AutoPilotWatcher:
    """
    Background thread that watches /proc and fires callbacks when a mapped
    game executable appears or disappears.

    Rules dict:  { "csgo": 1, "cyberpunk2077.exe": 2 }
                   ^exe name   ^0-based profile index

    on_switch(profile_index) is called from the watcher thread;
    callers must schedule GTK work with GLib.idle_add.
    """

    def __init__(
        self,
        rules: Dict[str, int],
        on_switch: Callable[[int, str], None],
        default_profile: int = 0,
    ) -> None:
        self._rules: Dict[str, int] = {k.lower(): v for k, v in rules.items()}
        self._on_switch = on_switch
        self._default_profile = default_profile
        self._active_profile: Optional[int] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._active_profile = None  # force re-evaluation on next tick
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="AutoPilot-Watcher"
        )
        self._thread.start()
        logger.info("AutoPilot watcher started (%.1fs poll interval)", POLL_INTERVAL)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=POLL_INTERVAL + 1)
        self._thread = None
        logger.info("AutoPilot watcher stopped")

    def request_stop(self) -> None:
        """Signal the thread to stop without waiting for it to wind down.

        Used when the application is quitting: joining would block the main
        loop for up to POLL_INTERVAL seconds, and the thread is a daemon so it
        dies with the process anyway. Setting the event is enough to stop any
        further switch callbacks from firing.
        """
        self._stop_event.set()
        logger.info("AutoPilot watcher stop requested")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def update_rules(self, rules: Dict[str, int], default_profile: int = 0) -> None:
        """Hot-reload rules without restarting the thread."""
        self._rules = {k.lower(): v for k, v in rules.items()}
        self._default_profile = default_profile
        self._active_profile = None  # force re-evaluation

    # ── Internal ───────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.wait(POLL_INTERVAL):
            self._tick()

    def _tick(self) -> None:
        if not self._rules:
            return

        running = _running_executables()
        matched_profile: Optional[int] = None
        matched_exe: Optional[str] = None

        for exe, profile_idx in self._rules.items():
            if exe in running:
                matched_profile = profile_idx
                matched_exe = exe
                break

        target = (
            matched_profile if matched_profile is not None else self._default_profile
        )
        label = matched_exe if matched_exe else "__default__"

        if target != self._active_profile:
            self._active_profile = target
            logger.info("AutoPilot: '%s' → profile %d", label, target)
            try:
                self._on_switch(target, label)
            except Exception as exc:
                logger.error("AutoPilot switch callback failed: %s", exc)
