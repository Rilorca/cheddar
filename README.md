# Cheddar for Logi Mice (and beyond!) 🧀🖱️

> **The missing G HUB experience for Linux.** Automatic per-game profile switching, endless custom profiles, and zero hassle.

**Cheddar** brings the smart, seamless gaming mouse experience of Logitech G HUB to Linux. Set up custom keybinds, DPIs, LEDs, and macros for each of your favorite games—Cheddar automatically detects when you launch or alt-tab into a game and switches your mouse profile on the fly, even with the window closed!

Built as a supercharged fork of [Piper](https://github.com/libratbag/piper) (the GTK mouse-configuration frontend), Cheddar keeps everything you love about Piper while adding our powerful **AutoPilot** engine and a lightweight background service.

Features
--------

- **Per-game profile switching.** Map a game to a profile; the mouse switches
  to it when the game runs and back to your default when it closes.
- **Follows the focused game.** With several games open, the one whose window
  is focused wins — alt-tab and the mouse follows.
- **Steam / Proton, Lutris and Heroic aware.** Detects Windows games running
  under Wine/Proton, not just native Linux binaries.
- **Pick games from a list.** The rule editor lists your installed games with
  their icons, so you don't have to type executable names.
- **Unlimited profiles.** The mouse only has a few onboard slots (3 on the
  G600); Cheddar stores as many named profiles as you want on your PC and
  loads them onto the mouse on demand — the same trick G HUB uses.
- **Runs in the background.** A systemd user service keeps switching profiles
  with no window open.

Requirements
------------

Cheddar is a frontend for **ratbagd** (from
[libratbag](https://github.com/libratbag/libratbag)), which does the actual
talking to the mouse. Your mouse must be
[supported by libratbag](https://github.com/libratbag/libratbag/tree/master/data/devices)
and have onboard profiles (most Logitech gaming mice do).

Runtime dependencies:

- `ratbagd` / `libratbag` (0.18 or newer)
- GTK 3, PyGObject
- Python 3 with the modules `lxml`, `evdev`, `cairo`, `gi`
- `xprop` — *optional but recommended*; enables focus-based switching. Without
  it, Cheddar still switches to whichever mapped game is running, just without
  the focus preference. It ships in `xorg-xprop` (Arch) / `x11-utils`
  (Debian/Ubuntu).

Installation
------------

There is no distribution package yet, so install by building from source. It's
a Python/GTK app — the build is quick and needs no compiler.

### Arch Linux / CachyOS / Manjaro

```sh
# 1. Dependencies
sudo pacman -S --needed meson ninja libratbag gtk3 python-gobject \
                        python-lxml python-evdev python-cairo xorg-xprop

# 2. Get the source and build
git clone https://github.com/Rilorca/cheddar.git
cd cheddar
meson setup builddir --prefix=/usr
ninja -C builddir
sudo ninja -C builddir install

# 3. Make sure ratbagd is running
sudo systemctl enable --now ratbagd
```

### Debian / Ubuntu

```sh
# 1. Dependencies
sudo apt install meson ninja-build ratbagd gir1.2-gtk-3.0 python3-gi \
                 python3-lxml python3-evdev python3-cairo x11-utils

# 2. Get the source and build
git clone https://github.com/Rilorca/cheddar.git
cd cheddar
meson setup builddir --prefix=/usr
ninja -C builddir
sudo ninja -C builddir install

# 3. Make sure ratbagd is running
sudo systemctl enable --now ratbagd
```

### Fedora

```sh
# 1. Dependencies
sudo dnf install meson ninja-build libratbag-ratbagd gtk3 python3-gobject \
                 python3-lxml python3-evdev python3-cairo xprop

# 2. Get the source and build
git clone https://github.com/Rilorca/cheddar.git
cd cheddar
meson setup builddir --prefix=/usr
ninja -C builddir
sudo ninja -C builddir install

# 3. Make sure ratbagd is running
sudo systemctl enable --now ratbagd
```

After installing, launch **Cheddar** from your application menu (or run
`cheddar`).

Enabling the background service
-------------------------------

For profiles to keep switching while Cheddar's window is closed, enable the
per-user service once:

```sh
systemctl --user enable --now cheddar-autopilot
```

It starts on every login and reads the same settings the GUI writes, applying
rule changes live. Check what it's doing with:

```sh
journalctl --user -u cheddar-autopilot -f
```

If you prefer, you can skip the service and just keep Cheddar's window open —
the AutoPilot tab has its own switch that does the same thing while it's open.

Using AutoPilot
---------------

1. Open Cheddar and select your mouse. Alongside the usual tabs (Resolutions,
   Buttons, LEDs, Advanced) you'll see a new **AutoPilot** tab.
2. **Create your profiles.** Set the mouse up how you want for a game in the
   Buttons / LEDs / Resolutions tabs, then open the profile menu (top-left)
   and click **Add profile** to save it under a name (e.g. "Overwatch"). Your
   profiles appear in that menu with a person icon; click one to load it, tweak
   it, and hit **Apply** to save the changes back.
3. **Set the default profile** in the AutoPilot tab — used when no mapped game
   is running.
4. **Add rules.** Click **+ Add rule**, pick a game from the list (or type its
   executable name), and choose the profile to switch to.
5. **Turn on the switch** ("Enable AutoPilot"). Done — launch a game and the
   mouse follows.

Settings live in `~/.config/cheddar/` (automatically migrated from
`~/.config/piper/` if you used an earlier build):

- `autopilot.json` — rules, default profile, on/off
- `autopilot_profiles.json` — your named profiles
- `backups/` — automatic backups of your mouse's onboard profiles

How it works (and one thing to know)
------------------------------------

Cheddar watches running processes via `/proc` (no root needed, works on
Wayland). For Wine/Proton games it reads the game's Windows-style path from the
process command line, since the Linux executable is just the Wine loader.

Because the mouse only has a few onboard slots, your named profiles are stored
on your PC and written into **one reserved onboard slot** when needed (the last
slot by default). While AutoPilot is enabled that slot is hidden from the
profile menu, because Cheddar manages it and overwrites it on game launches. If
you want a different slot, set `"scratch_slot"` in
`~/.config/cheddar/autopilot.json`. Your other onboard slots are never touched.

Troubleshooting
---------------

**"Cannot find any devices" / the mousetrap screen.** ratbagd isn't running or
can't see your mouse. Start it with `sudo systemctl start ratbagd` and replug
the mouse.

**Solaar breaks detection (Logitech mice).** If [Solaar](https://pwr-solaar.github.io/Solaar/)
is running when ratbagd starts, ratbagd may fail to read the mouse
(`Error while requesting profile: -32`, `invalid dpi list`) and Cheddar shows
no devices. This looks like a libratbag bug but isn't — the fix is to **stop
Solaar first**, then `sudo systemctl restart ratbagd` (or replug the mouse).
Keep Solaar out of autostart, or configure it to ignore the mouse, if you use
both.

**A game isn't detected.** Watch the daemon log while launching it:
`journalctl --user -u cheddar-autopilot -f`. Then add a rule for the executable
name you see. Names are case-insensitive and the `.exe` is optional.

Contributing / development
--------------------------

For quick iteration without installing, `meson setup builddir` then run the
in-tree binary:

```sh
ninja -C builddir
./builddir/cheddar.devel
```

Code is formatted with `black` and linted with `ruff` (run `meson test -C
builddir`). Cheddar's own code lives in `cheddar/autopilot_*.py` and
`data/cheddar-autopilot.service`, with small edits to
`cheddar/mouseperspective.py` and `cheddar/window.py`.

License
-------

GPL-2.0-or-later, same as upstream Piper. See [COPYING](COPYING).
Cheddar is based on [Piper](https://github.com/libratbag/piper) by the
libratbag project.
