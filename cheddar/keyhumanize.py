# SPDX-License-Identifier: GPL-2.0-or-later
#
# keyhumanize.py — part of Cheddar fork
#
# Turns libratbag's raw evdev names and macros ("↕KEY_SEMICOLON",
# "↓KEY_LEFTCTRL ↕KEY_V ↑KEY_LEFTCTRL") into human-readable button labels
# ("Semicolon ;", "Paste (Ctrl+V)") for the Mouse setup view.

from gettext import gettext as _

from .ratbagd import RatbagdButton, evcode_to_str

# Friendly names for keys whose evdev name isn't already obvious. Anything not
# here falls back to a title-cased version of the stripped evdev name.
_KEY_NAMES = {
    "SEMICOLON": "Semicolon ;",
    "APOSTROPHE": "Apostrophe '",
    "GRAVE": "Backtick `",
    "MINUS": "Minus −",
    "EQUAL": "Equal =",
    "COMMA": "Comma ,",
    "DOT": "Period .",
    "SLASH": "Slash /",
    "BACKSLASH": "Backslash \\",
    "LEFTBRACE": "Bracket [",
    "RIGHTBRACE": "Bracket ]",
    "SPACE": "Space",
    "ENTER": "Enter",
    "ESC": "Esc",
    "TAB": "Tab",
    "BACKSPACE": "Backspace",
    "DELETE": "Delete",
    "INSERT": "Insert",
    "HOME": "Home",
    "END": "End",
    "PAGEUP": "Page Up",
    "PAGEDOWN": "Page Down",
    "UP": "Up arrow",
    "DOWN": "Down arrow",
    "LEFT": "Left arrow",
    "RIGHT": "Right arrow",
    "CAPSLOCK": "Caps Lock",
}

_MODIFIERS = {
    "LEFTCTRL": "Ctrl",
    "RIGHTCTRL": "Ctrl",
    "LEFTSHIFT": "Shift",
    "RIGHTSHIFT": "Shift",
    "LEFTALT": "Alt",
    "RIGHTALT": "Alt",
    "LEFTMETA": "Super",
    "RIGHTMETA": "Super",
}

# Well-known modifier+key combos, keyed by "Mod+KEY".
_COMBOS = {
    "Ctrl+C": _("Copy (Ctrl+C)"),
    "Ctrl+V": _("Paste (Ctrl+V)"),
    "Ctrl+X": _("Cut (Ctrl+X)"),
    "Ctrl+Z": _("Undo (Ctrl+Z)"),
    "Ctrl+Y": _("Redo (Ctrl+Y)"),
    "Ctrl+A": _("Select all (Ctrl+A)"),
    "Ctrl+S": _("Save (Ctrl+S)"),
}


def _strip(evname: str) -> str:
    for prefix in ("KEY_", "BTN_"):
        if evname.startswith(prefix):
            return evname[len(prefix) :]
    return evname


def friendly_key(evcode: int) -> str:
    """Human label for a single evdev keycode."""
    return _friendly_name(evcode_to_str(evcode))


def _friendly_name(evname: str) -> str:
    core = _strip(evname)
    if core in _KEY_NAMES:
        return _KEY_NAMES[core]
    if core in _MODIFIERS:
        return _MODIFIERS[core]
    if len(core) == 1:  # single letter or digit
        return core
    if core.startswith("KP"):  # numpad
        return "Num " + core[2:].title()
    if len(core) <= 3 and core[0] == "F" and core[1:].isdigit():
        return core  # F1..F12
    return core.title()


def _short_mod(evname: str) -> str:
    return _MODIFIERS.get(_strip(evname), _friendly_name(evname))


def humanize_macro(macro) -> str:
    """Human label for a RatbagdMacro. Collapses press+release into a tap,
    recognizes single keys and common modifier combos, and keeps long macros
    short."""
    events = list(macro.keys)

    # Collapse into an ordered sequence of tokens.
    seq = []  # ("tap", ev) | ("down", ev) | ("up", ev) | ("wait", ms)
    i = 0
    while i < len(events):
        t, v = events[i]
        if (
            t == RatbagdButton.Macro.KEY_PRESS
            and i + 1 < len(events)
            and events[i + 1] == (RatbagdButton.Macro.KEY_RELEASE, v)
        ):
            seq.append(("tap", v))
            i += 2
        elif t == RatbagdButton.Macro.KEY_PRESS:
            seq.append(("down", v))
            i += 1
        elif t == RatbagdButton.Macro.KEY_RELEASE:
            seq.append(("up", v))
            i += 1
        else:
            seq.append(("wait", v))
            i += 1

    if not seq:
        return _("Empty macro")

    # A single tapped key: show just the key.
    if len(seq) == 1 and seq[0][0] == "tap":
        return friendly_key(seq[0][1])

    # Modifier held around a single tap: "Mod + Key" / recognized combo.
    downs = [v for kind, v in seq if kind == "down"]
    ups = [v for kind, v in seq if kind == "up"]
    taps = [v for kind, v in seq if kind == "tap"]
    if len(taps) == 1 and downs and set(downs) == set(ups):
        mods = " + ".join(_short_mod(evcode_to_str(d)) for d in downs)
        key = friendly_key(taps[0])
        combo_key = f"{mods}+{key}"
        if combo_key in _COMBOS:
            return _COMBOS[combo_key]
        return f"{mods} + {key}"

    # Anything more elaborate: a compact "Macro · a b c…" preview.
    parts = []
    for kind, v in seq:
        if kind == "wait":
            continue
        parts.append(friendly_key(v))
        if len(parts) >= 4:
            parts.append("…")
            break
    return _("Macro · {}").format(" ".join(parts))
