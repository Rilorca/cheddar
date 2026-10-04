# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilot_profiles.py — part of Cheddar AutoPilot fork
#
# Software profiles, the trick behind G HUB's "unlimited profiles": the mouse
# only has a few onboard slots, so extra profiles live on the PC as JSON and
# get written into a designated onboard slot right before activating it.
#
# A software profile captures everything Cheddar can configure on a profile:
# report rate, resolutions, every button mapping (including macros) and LEDs.
# Store: ~/.config/cheddar/autopilot_profiles.json  {name: profile-data}

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

from .ratbagd import RatbagdButton, RatbagdDevice, RatbagdMacro, RatbagdProfile

logger = logging.getLogger(__name__)

_STORE_DIR = os.path.expanduser("~/.config/cheddar")
_STORE_FILE = os.path.join(_STORE_DIR, "autopilot_profiles.json")
# Records which user profile (if any) is currently written on the scratch
# slot, so the GUI can label it by name even when the daemon did the switch.
_STATE_FILE = os.path.join(_STORE_DIR, "autopilot_state.json")

# Rule targets: an int selects an onboard profile by index; "sw:<name>"
# selects a stored software profile.
SW_PREFIX = "sw:"
RuleTarget = Union[int, str]


# ── Store ──────────────────────────────────────────────────────────────────────


def load_store() -> Dict[str, Dict]:
    try:
        with open(_STORE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_store(store: Dict[str, Dict]) -> None:
    os.makedirs(_STORE_DIR, exist_ok=True)
    try:
        with open(_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error("could not save software profiles: %s", e)


def active_user_profile() -> Optional[str]:
    """Name of the user profile currently on the scratch slot, or None if an
    onboard profile is active. Written by activate_target(), so the GUI sees
    switches the daemon made too."""
    try:
        with open(_STATE_FILE, encoding="utf-8") as f:
            name = json.load(f).get("active_user_profile")
        return name if isinstance(name, str) else None
    except (OSError, ValueError):
        return None


def _set_active_user_profile(name: Optional[str]) -> None:
    os.makedirs(_STORE_DIR, exist_ok=True)
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"active_user_profile": name}, f)
    except OSError as e:
        logger.error("could not save autopilot state: %s", e)


# ── Capture ────────────────────────────────────────────────────────────────────


def capture_profile(profile: RatbagdProfile) -> Dict[str, Any]:
    """Serialize an onboard profile's full configuration."""
    data: Dict[str, Any] = {"version": 1}

    data["report_rate"] = profile.report_rate

    resolutions: List[Dict] = []
    for res in profile.resolutions:
        resolutions.append(
            {
                "index": res.index,
                "resolution": list(res.resolution),
                "active": bool(res.is_active),
                "default": bool(res.is_default),
                "disabled": bool(res.is_disabled),
            }
        )
    data["resolutions"] = resolutions

    buttons: List[Dict] = []
    for btn in profile.buttons:
        t = btn.action_type
        entry: Dict[str, Any] = {"index": btn.index, "type": int(t)}
        if t == RatbagdButton.ActionType.BUTTON:
            entry["value"] = btn.mapping
        elif t == RatbagdButton.ActionType.KEY:
            entry["value"] = btn.key
        elif t == RatbagdButton.ActionType.SPECIAL:
            entry["value"] = int(btn.special)
        elif t == RatbagdButton.ActionType.MACRO:
            entry["value"] = [list(k) for k in btn.macro.keys]
        buttons.append(entry)
    data["buttons"] = buttons

    leds: List[Dict] = []
    for led in profile.leds:
        leds.append(
            {
                "index": led.index,
                "mode": int(led.mode),
                "color": list(led.color),
                "effect_duration": led.effect_duration,
                "brightness": led.brightness,
            }
        )
    data["leds"] = leds

    return data


# ── Apply ──────────────────────────────────────────────────────────────────────


def apply_profile(data: Dict[str, Any], profile: RatbagdProfile) -> None:
    """Write a captured configuration into an onboard profile slot.

    Only touches properties that differ, to keep the D-Bus/commit traffic
    (and flash writes on the mouse) to a minimum. The caller commits.
    """
    rate = data.get("report_rate")
    rates = profile.report_rates or []
    if rate and rate != profile.report_rate and (rate in rates or not rates):
        profile.report_rate = rate

    by_index = {r["index"]: r for r in data.get("resolutions", [])}
    for res in profile.resolutions:
        want = by_index.get(res.index)
        if want is None:
            continue
        target = tuple(want["resolution"])
        if len(target) == len(res.resolution) and target != tuple(res.resolution):
            res.resolution = target
        if want.get("disabled", False) != res.is_disabled and (
            res.CAP_DISABLE in res.capabilities or not want.get("disabled")
        ):
            res.set_disabled(want.get("disabled", False))
        if want.get("default") and not res.is_default:
            res.set_default()
        if want.get("active") and not res.is_active:
            res.set_active()

    by_index = {b["index"]: b for b in data.get("buttons", [])}
    for btn in profile.buttons:
        want = by_index.get(btn.index)
        if want is None:
            continue
        t = want["type"]
        value = want.get("value")
        if t == int(RatbagdButton.ActionType.NONE):
            if not btn.disabled:
                btn.disable()
        elif t == int(RatbagdButton.ActionType.BUTTON):
            if btn.mapping != value:
                btn.mapping = value
        elif t == int(RatbagdButton.ActionType.KEY):
            if btn.key != value:
                btn.key = value
        elif t == int(RatbagdButton.ActionType.SPECIAL):
            if btn.special != value:
                btn.special = value
        elif t == int(RatbagdButton.ActionType.MACRO):
            keys = [tuple(k) for k in value or []]
            current = btn.macro
            if current is None or list(current.keys) != keys:
                macro = RatbagdMacro()
                for ktype, kval in keys:
                    macro.append(ktype, kval)
                btn.macro = macro

    by_index = {led_d["index"]: led_d for led_d in data.get("leds", [])}
    for led in profile.leds:
        want = by_index.get(led.index)
        if want is None:
            continue
        modes = led.modes or []
        if want.get("mode") is not None and want["mode"] != int(led.mode) and (want["mode"] in modes or not modes):
            led.mode = want["mode"]
        if want.get("color") is not None and tuple(want["color"]) != tuple(led.color or ()):
            led.color = tuple(want["color"])
        if want.get("effect_duration") is not None and want["effect_duration"] != led.effect_duration:
            led.effect_duration = want["effect_duration"]
        if want.get("brightness") is not None and want["brightness"] != led.brightness:
            led.brightness = want["brightness"]


# ── Active-resolution healing ────────────────────────────────────────────────


def ensure_valid_active_resolution(profile) -> bool:
    """Make sure the profile has exactly one usable active DPI stage.

    After a profile switch the newly active profile may have no active
    resolution at all (or point at a disabled one); on the hardware the
    DPI-cycle button then appears dead until something re-asserts a
    valid stage. Picks the current active one if usable, else the
    default one if enabled, else the first enabled one.

    Returns True if it changed anything (the caller should commit).
    Works duck-typed on both RatbagdProfile and test doubles.
    """
    resolutions = list(profile.resolutions or [])
    if not resolutions:
        return False
    try:
        active = profile.active_resolution
    except Exception:
        active = None
    if (
        active is not None
        and active in resolutions
        and not active.is_disabled
        and active.is_active
        and all(not r.is_active for r in resolutions if r is not active)
    ):
        return False
    target = None
    if active is not None and active in resolutions and not active.is_disabled:
        target = active
    else:
        for res in resolutions:
            if res.is_default and not res.is_disabled:
                target = res
                break
        if target is None:
            for res in resolutions:
                if not res.is_disabled:
                    target = res
                    break
    if target is None:
        return False
    if target.is_active and all(
        not r.is_active for r in resolutions if r is not target
    ):
        return False
    target.set_active()
    return True


# ── Rule-target activation (shared by the GUI page and the daemon) ────────────


def schedule_settled_recommit(
    device, expected_index: int, delay: float = 2.0
) -> None:
    """Re-commit a profile switch once the mouse has settled.

    Proven by live G600 debugging: the Commit issued immediately after
    Profile.SetActive is lost by the firmware (the on-mouse DPI-cycle
    button stays dead even though ratbagd reports everything correct),
    while a second Commit issued a couple of seconds later — e.g. the
    manual "Apply" for a pending IsDirty at GUI startup — unwedges it.
    Fires once; skips if the device moved to another profile meanwhile.
    Daemon thread so it never blocks interpreters/tests on exit.
    Works duck-typed on RatbagdDevice and test doubles.
    """

    def _cb() -> None:
        try:
            active = device.active_profile
            if active is not None and active.index == expected_index:
                device.commit()
                logger.info(
                    "settled re-commit for profile %s done", expected_index
                )
        except Exception as e:
            logger.error("settled re-commit failed: %s", e)

    t = threading.Timer(delay, _cb)
    t.daemon = True
    t.start()


def is_software_target(target: RuleTarget) -> bool:
    return isinstance(target, str) and target.startswith(SW_PREFIX)


def target_label(target: RuleTarget) -> str:
    """Human-readable name of a rule target (software profile name as-is;
    onboard targets are labeled by the caller, which knows the device)."""
    return target[len(SW_PREFIX) :] if is_software_target(target) else str(target)


def scratch_slot_for(device: RatbagdDevice, config: Dict) -> int:
    """The onboard slot software profiles get written into. Defaults to the
    last slot; override with "scratch_slot" in autopilot.json."""
    n = len(device.profiles)
    if n == 0:
        return 0
    slot = config.get("scratch_slot")
    if isinstance(slot, int) and 0 <= slot < n:
        return slot
    return n - 1


def activate_target(device: RatbagdDevice, target: RuleTarget, config: Dict) -> None:
    """Switch the device to a rule target: activate an onboard profile, or
    write a software profile into the scratch slot and activate that.
    Raises on unknown software profiles; the caller reports errors."""
    if not device.profiles:
        raise IndexError(f"Device {device.name} has no profiles")

    if is_software_target(target):
        name = target[len(SW_PREFIX) :]
        data = load_store().get(name)
        if data is None:
            raise KeyError(f"software profile '{name}' does not exist")
        slot = scratch_slot_for(device, config)
        for profile in device.profiles:
            if profile.index == slot:
                apply_profile(data, profile)
                try:
                    ensure_valid_active_resolution(profile)
                except Exception as e:
                    logger.error("could not heal active resolution: %s", e)
                profile.set_active()
                device.commit()
                schedule_settled_recommit(device, slot)
                _set_active_user_profile(name)
                logger.info("software profile '%s' -> slot %d", name, slot)
                return
        raise IndexError(f"scratch slot {slot} not found")

    index = int(target)
    for profile in device.profiles:
        if profile.index == index:
            # NOTE: the Commit IS required here (verified with live dumps
            # on a G600): Profile.SetActive alone only flips ratbagd's
            # in-memory IsActive flag, but the mouse hardware stays on the
            # previous profile — so a DPI button that only exists on the
            # requested profile appears dead. Commit flushes to hardware.
            profile.set_active()
            try:
                ensure_valid_active_resolution(profile)
            except Exception as e:
                logger.error("could not heal active resolution: %s", e)
            device.commit()
            schedule_settled_recommit(device, index)
            _set_active_user_profile(None)
            return
    raise IndexError(f"profile {index} not found on {device.name}")
