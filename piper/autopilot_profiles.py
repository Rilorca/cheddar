# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilot_profiles.py — part of Piper AutoPilot fork
#
# Software profiles, the trick behind G HUB's "unlimited profiles": the mouse
# only has a few onboard slots, so extra profiles live on the PC as JSON and
# get written into a designated onboard slot right before activating it.
#
# A software profile captures everything Piper can configure on a profile:
# report rate, resolutions, every button mapping (including macros) and LEDs.
# Store: ~/.config/piper/autopilot_profiles.json  {name: profile-data}

import json
import logging
import os
from typing import Any, Dict, List, Union

from .ratbagd import RatbagdButton, RatbagdDevice, RatbagdMacro, RatbagdProfile

logger = logging.getLogger(__name__)

_STORE_DIR = os.path.expanduser("~/.config/piper")
_STORE_FILE = os.path.join(_STORE_DIR, "autopilot_profiles.json")

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
    if rate and rate != profile.report_rate and rate in profile.report_rates:
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
        if want["mode"] != int(led.mode) and want["mode"] in led.modes:
            led.mode = want["mode"]
        if tuple(want["color"]) != tuple(led.color):
            led.color = tuple(want["color"])
        if want["effect_duration"] != led.effect_duration:
            led.effect_duration = want["effect_duration"]
        if want["brightness"] != led.brightness:
            led.brightness = want["brightness"]


# ── Rule-target activation (shared by the GUI page and the daemon) ────────────


def is_software_target(target: RuleTarget) -> bool:
    return isinstance(target, str) and target.startswith(SW_PREFIX)


def target_label(target: RuleTarget) -> str:
    """Human-readable name of a rule target (software profile name as-is;
    onboard targets are labeled by the caller, which knows the device)."""
    return target[len(SW_PREFIX) :] if is_software_target(target) else str(target)


def scratch_slot_for(device: RatbagdDevice, config: Dict) -> int:
    """The onboard slot software profiles get written into. Defaults to the
    last slot; override with "scratch_slot" in autopilot.json."""
    slot = config.get("scratch_slot")
    n = len(device.profiles)
    if isinstance(slot, int) and 0 <= slot < n:
        return slot
    return n - 1


def activate_target(device: RatbagdDevice, target: RuleTarget, config: Dict) -> None:
    """Switch the device to a rule target: activate an onboard profile, or
    write a software profile into the scratch slot and activate that.
    Raises on unknown software profiles; the caller reports errors."""
    if is_software_target(target):
        name = target[len(SW_PREFIX) :]
        data = load_store().get(name)
        if data is None:
            raise KeyError(f"software profile '{name}' does not exist")
        slot = scratch_slot_for(device, config)
        for profile in device.profiles:
            if profile.index == slot:
                apply_profile(data, profile)
                profile.set_active()
                device.commit()
                logger.info("software profile '%s' -> slot %d", name, slot)
                return
        raise IndexError(f"scratch slot {slot} not found")

    index = int(target)
    for profile in device.profiles:
        if profile.index == index:
            profile.set_active()
            device.commit()
            return
    raise IndexError(f"profile {index} not found on {device.name}")
