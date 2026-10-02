# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilot_watcher.py — part of Cheddar AutoPilot fork
# Polls /proc every POLL_INTERVAL seconds to detect running game executables
# and fires callbacks to switch ratbagd profiles accordingly.

import os
import re
import subprocess
import threading
import logging
from typing import Callable, Dict, Optional, Set, Union

# A rule target: onboard profile index (int) or software profile ("sw:<name>")
RuleTarget = Union[int, str]

logger = logging.getLogger(__name__)

POLL_INTERVAL = 2.0  # seconds


_ARCH_SUFFIX = re.compile(
    r"[-_]?(?:x86_64|x86|x64|64|32|win64|win32|shipping)+$", re.IGNORECASE
)


def _add_name(exes: Set[str], name: str) -> None:
    """Add a lowercase executable name, plus aliases (without .exe, without
    architecture suffixes, and without spaces) so rules match whether or not
    the user typed the extension, architecture, or spaces."""
    name = name.lower()
    if not name:
        return
    exes.add(name)
    has_exe = name.endswith(".exe")
    stem = name[:-4] if has_exe else name
    exes.add(stem)

    # Alias without architecture suffix (e.g. heroesofthestorm_x64 -> heroesofthestorm)
    base = _ARCH_SUFFIX.sub("", stem)
    if base and base != stem:
        exes.add(base)
        exes.add(base + ".exe")

    # Alias without spaces (e.g. "heroes of the storm" -> "heroesofthestorm")
    if " " in name:
        exes.add(name.replace(" ", ""))
        if has_exe:
            exes.add(stem.replace(" ", ""))


def _basename_any_os(path: str) -> str:
    """Basename that also understands Windows-style paths, as found in the
    cmdline of Wine/Proton processes (e.g. 'Z:\\Games\\Foo\\foo.exe')."""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def is_flatpak() -> bool:
    return os.path.exists("/.flatpak-info")


def _scan_processes() -> Dict[int, Set[str]]:
    """Map every PID in /proc to the lowercase names it can be known by.

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
    procs: Dict[int, Set[str]] = {}
    if is_flatpak():
        # Inside Flatpak sandbox, host /proc is accessed via flatpak-spawn --host
        cmd = [
            "flatpak-spawn", "--host", "python3", "-c",
            "import os, sys\n"
            "for entry in os.scandir('/proc'):\n"
            "    if not entry.name.isdigit(): continue\n"
            "    try:\n"
            "        exe = os.readlink(f'/proc/{entry.name}/exe')\n"
            "    except OSError:\n"
            "        exe = ''\n"
            "    try:\n"
            "        with open(f'/proc/{entry.name}/cmdline', 'rb') as f:\n"
            "            argv0 = f.read(4096).split(b'\\0', 1)[0].decode('utf-8', 'replace')\n"
            "    except OSError:\n"
            "        argv0 = ''\n"
            "    if exe or argv0:\n"
            "        sys.stdout.write(f'{entry.name}\\t{os.path.basename(exe)}\\t{argv0}\\n')\n"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            for line in res.stdout.splitlines():
                parts = line.split("\t", 2)
                if len(parts) >= 2 and parts[0].isdigit():
                    pid = int(parts[0])
                    exe_name = parts[1]
                    argv0 = parts[2] if len(parts) > 2 else ""
                    names: Set[str] = set()
                    if exe_name:
                        _add_name(names, exe_name)
                    if argv0:
                        _add_name(names, _basename_any_os(argv0))
                    if names:
                        procs[pid] = names
            return procs
        except Exception as e:
            logger.debug("Error scanning host /proc via flatpak-spawn: %s", e)
            return procs

    try:
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit():
                continue
            names: Set[str] = set()
            try:
                exe_path = os.readlink(f"/proc/{entry.name}/exe")
                _add_name(names, os.path.basename(exe_path))
            except OSError:
                pass
            try:
                with open(f"/proc/{entry.name}/cmdline", "rb") as f:
                    argv0 = f.read(4096).split(b"\0", 1)[0]
                if argv0:
                    _add_name(names, _basename_any_os(argv0.decode("utf-8", "replace")))
            except OSError:
                pass
            if names:
                procs[int(entry.name)] = names
    except Exception as e:
        logger.debug("Error scanning /proc: %s", e)
    return procs


def _running_executables() -> Set[str]:
    """Union of every name from _scan_processes()."""
    exes: Set[str] = set()
    for names in _scan_processes().values():
        exes |= names
    return exes


_WINDOW_ID_RE = re.compile(r"0x[0-9a-fA-F]+")
_PID_RE = re.compile(r"= (\d+)$")


# _focused_pid() return values: a PID when the focused window exposes one;
# NO_PID when there is a focused window but it carries no X PID (a
# Wayland-native app — i.e. definitely not a Proton/Wine game); None when
# focus could not be determined at all (xprop missing/failed).
NO_PID = 0


def _focused_pid() -> Optional[int]:
    """PID owning the focused window, NO_PID for a PID-less window, or None.

    Uses the X11 _NET_ACTIVE_WINDOW / _NET_WM_PID properties via xprop.
    Proton/Wine games run on XWayland, so a focused game always exposes its
    PID even on a Wayland session. A focused Wayland-native window (browser,
    terminal, desktop) leaves the X active window without a PID — that is a
    positive "something that isn't a game has focus" signal, distinct from
    None where callers should fall back to any-running matching.
    """
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    xprop_cmd = ["flatpak-spawn", "--host", "xprop"] if is_flatpak() else ["xprop"]
    try:
        out = subprocess.run(
            xprop_cmd + ["-root", "_NET_ACTIVE_WINDOW"],
            capture_output=True,
            text=True,
            timeout=2,
            env=env,
        ).stdout
        m = _WINDOW_ID_RE.search(out)
        if not m:
            return None
        if int(m.group(0), 16) == 0:  # no active X window at all
            return NO_PID
        out = subprocess.run(
            xprop_cmd + ["-id", m.group(0), "_NET_WM_PID"],
            capture_output=True,
            text=True,
            timeout=2,
            env=env,
        ).stdout
        m = _PID_RE.search(out.strip())
        return int(m.group(1)) if m else NO_PID
    except (OSError, subprocess.SubprocessError):
        return None


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
        rules: Dict[str, RuleTarget],
        on_switch: Callable[[RuleTarget, str], None],
        default_profile: int = 0,
    ) -> None:
        self._rules: Dict[str, RuleTarget] = {k.lower(): v for k, v in rules.items()}
        self._on_switch = on_switch
        self._default_profile = default_profile
        self._active_profile: Optional[RuleTarget] = None
        self._last_matched_exe: Optional[str] = None
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

    def update_rules(
        self, rules: Dict[str, RuleTarget], default_profile: int = 0
    ) -> None:
        """Hot-reload rules without restarting the thread."""
        self._rules = {k.lower(): v for k, v in rules.items()}
        self._default_profile = default_profile
        self._active_profile = None  # force re-evaluation
        self._last_matched_exe = None

    # ── Internal ───────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.wait(POLL_INTERVAL):
            try:
                self._tick()
            except Exception as e:
                logger.error("AutoPilot watcher error in tick: %s", e)

    def _tick(self) -> None:
        if not self._rules:
            return

        procs = _scan_processes()
        matched_profile: Optional[RuleTarget] = None
        matched_exe: Optional[str] = None

        # Focus decides, matching G HUB's behavior: the game owning the
        # focused window wins, and focusing anything that is not a mapped
        # game (desktop, browser, another app) returns to the default
        # profile even while games keep running in the background.
        focused = _focused_pid()
        if focused is not None:
            focused_names = procs.get(focused, set()) if focused > 0 else set()
            for exe, profile_idx in self._rules.items():
                if exe in focused_names or exe.replace(" ", "") in focused_names:
                    matched_profile = profile_idx
                    matched_exe = exe
                    break
            # No match on a positively identified focus → fall through with
            # no game matched, which lands on the default profile below.
        else:
            # Focus unknown (xprop unavailable/failed): fall back to
            # any-running matching, preferring the game matched last time
            # so the profile doesn't flip between two running games.
            running: Set[str] = set()
            for names in procs.values():
                running |= names
            if self._last_matched_exe and (
                self._last_matched_exe in running
                or self._last_matched_exe.replace(" ", "") in running
            ):
                matched_exe = self._last_matched_exe
                matched_profile = self._rules.get(matched_exe)
            if matched_profile is None:
                for exe, profile_idx in self._rules.items():
                    if exe in running or exe.replace(" ", "") in running:
                        matched_profile = profile_idx
                        matched_exe = exe
                        break

        self._last_matched_exe = matched_exe

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
