Piper
=====

Piper is a GTK+ application to configure gaming mice. Piper is merely a
graphical frontend to the ratbagd DBus daemon, see [the libratbag
README](https://github.com/libratbag/libratbag/blob/master/README.md#running-ratbagd-as-dbus-activated-systemd-service)
for instructions on how to run ratbagd.

If you are running piper from git, we recommend using libratbag from git
as well to make sure the latest bugfixes are applied.

Supported Devices
=================
Piper is merely a frontend, the list of supported devices depends on
libratbag. See [the libratbag device
files](https://github.com/libratbag/libratbag/tree/master/data/devices) for
a list of all known devices.  The device-specific protocols usually have to
be reverse-engineered and the features available may vary to the
manufacturer's advertized features.

Screenshots
===========

![resolution configuration screenshot](https://github.com/libratbag/piper/blob/wiki/screenshots/piper-resolutionpage.png)

![button configuration screenshot](https://github.com/libratbag/piper/blob/wiki/screenshots/piper-buttonpage.png)

![LED configuration screenshot](https://github.com/libratbag/piper/blob/wiki/screenshots/piper-ledpage.png)

And if you see the mousetrap, something isn't right. Usually this means that
either ratbagd is not running (like in this screenshot), ratbagd needs to be
updated to a newer version, or some other unexpected error occured.

![The error page](https://github.com/libratbag/piper/blob/wiki/screenshots/piper-errorpage.png)

Installing Piper
================

See [our Wiki](https://github.com/libratbag/piper/wiki/Installation) for how to install Piper.

Building Piper from git
=======================

Piper uses the [meson build system](http://mesonbuild.com/). Run the following
commands to clone Piper and initialize the build:

```sh
git clone https://github.com/libratbag/piper.git
cd piper
meson builddir --prefix=/usr/
```

To build or re-build after code-changes and install, run:

```sh
ninja -C builddir
sudo ninja -C builddir install
```

Note: `builddir` is the build output directory and can be changed to any other
directory name.

See [our Wiki](https://github.com/libratbag/piper/wiki/Installation) for what
to do when you encounter missing dependencies.

Contributing
============

Yes please. It's best to contact us first to see what you could do. Note that
the devices displayed by Piper come from libratbag.

For quicker development iteration, there is a special binary `piper.devel`
that uses data files from the git directory. This removes the need to
install piper after every code change.

```sh
ninja -C builddir
./builddir/piper.devel
```
Note that this still requires ratbagd to run on the system bus.

Piper tries to conform to Python's PEP8 style guide using the `black` formatter.
Checking if code is formatted is done as a part of the test suite.

You can check if your code passes tests before submitting changes using the
following command:

```sh
meson test -C builddir
```

Source
======

```sh
git clone https://github.com/libratbag/piper.git
```

Bugs
====

Bugs can be reported in the issue tracker on our GitHub repo:
https://github.com/libratbag/piper/issues

License
=======

Licensed under the GPLv2. See the
[COPYING](https://github.com/libratbag/piper/blob/master/COPYING) file for the
full license information.

---

## AutoPilot — automatic profile switching (fork addition)

This fork adds an **AutoPilot** tab to every device's configuration screen.

### What it does

AutoPilot watches running processes (`/proc`) every 2 seconds. When a mapped
game executable is detected, it automatically switches the G600 to the
configured profile. When the game closes, it returns to the default profile.

Both native Linux games and **Wine/Proton games** (Steam, Lutris, Heroic) are
detected: for Proton titles `/proc/PID/exe` points at the wine preloader, so
the watcher also inspects the Windows-style path in `argv[0]`
(e.g. `Z:\Games\Cyberpunk 2077\bin\x64\Cyberpunk2077.exe` → `cyberpunk2077.exe`).
Rules match case-insensitively and the `.exe` extension is optional.

### How to use

1. Open Piper as usual (`piper` or `./piper.in`)
2. Select your G600 — you'll see the normal tabs (Resolutions, Buttons, LEDs,
   Advanced) **plus a new "AutoPilot" tab**
3. In the AutoPilot tab:
   - Set the **Default Profile** (used when no game is running)
   - Click **+ Add rule** and map an executable (e.g. `cs2`) to a profile
   - Toggle **Enable AutoPilot** — the watcher starts immediately
4. Rules are saved to `~/.config/piper/autopilot.json` and auto-restored

### Headless daemon (no GUI needed)

Profile switching should not require keeping a window open — that's the job
G HUB's background service does on Windows. This fork ships a headless daemon
that runs the same watcher against ratbagd directly:

```sh
python3 -m piper.autopilot_daemon        # foreground, Ctrl+C to stop
```

It reads the same `~/.config/piper/autopilot.json` the GUI writes and reloads
it live when you edit rules in the AutoPilot tab. Running it alongside the GUI
is harmless (switches are idempotent).

A systemd **user** unit is installed with the app; enable it to start on login:

```sh
systemctl --user enable --now piper-autopilot
```

### Files added / modified

| File | Change |
|---|---|
| `piper/autopilotpage.py` | New — the AutoPilot tab widget |
| `piper/autopilot_watcher.py` | New — `/proc` scanner background thread (native + Wine/Proton) |
| `piper/autopilot_config.py` | New — JSON config persistence |
| `piper/autopilot_daemon.py` | New — headless daemon (`python3 -m piper.autopilot_daemon`) |
| `data/piper-autopilot.service` | New — systemd user unit for the daemon |
| `piper/mouseperspective.py` | Modified — adds AutoPilot tab to stack |
| `piper/window.py` | Modified — perspective shutdown on window destroy |

### Why /proc?

- No root required
- Works on Wayland (no X11 dependency)
- No extra dependencies beyond what Piper already needs

### Known conflict: Solaar (Arch/CachyOS)

If Solaar is running when ratbagd starts, ratbagd may fail to enumerate the
G600 (`Error while requesting profile: -32`, `invalid dpi list`) and Piper
will report no devices — the symptoms mimic upstream libratbag bug #1291 but
the fix is local: stop Solaar **first**, then `sudo systemctl restart ratbagd`
(or replug the mouse). Keep Solaar out of autostart, or configure it to ignore
the G600.
