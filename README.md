<p align="center">
  <img src="data/io.github.rilorca.Cheddar.svg" width="128" height="128" alt="Cheddar Logo">
</p>

<h1 align="center">Cheddar</h1>

<p align="center">
  <strong>The Missing Logitech G HUB Experience for Linux 🧀🖱️</strong><br>
  <em>Smart per-game profile switching, endless custom profiles, and zero-hassle gaming mouse management.</em>
</p>

<p align="center">
  <a href="#why-cheddar">Why Cheddar?</a> •
  <a href="#screenshots">Screenshots</a> •
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#troubleshooting">Troubleshooting</a>
</p>

---

## Why Cheddar?

On Windows, Logitech G HUB automatically detects when you launch a game and reconfigures your mouse instantly with your custom keybindings, DPI resolutions, and macros. On Linux, gamers were previously stuck with static onboard profiles or manual tools.

**Cheddar changes the game.** Built with modern Libadwaita aesthetics as a supercharged evolution of [Piper](https://github.com/libratbag/piper), Cheddar brings full-featured automation and mouse tuning to the Linux desktop:

- 🎮 **Zero-Effort AutoPilot:** Launch Steam, Proton, Lutris, Heroic, or Faugus Launcher games, and your mouse profile switches instantly in the background. Alt-tab between games or back to the desktop, and your settings follow seamlessly.
- ♾️ **Unlimited Game Profiles:** Don't let your mouse's 3 onboard memory slots limit your gaming library. Cheddar stores unlimited custom profiles on your PC and dynamically writes them onto your mouse hardware on the fly.
- ⚡ **Blazing Fast & Lightweight:** Zero Electron bloat. Native GTK styling with an ultra-lightweight `/proc` watcher that consumes near-zero CPU and RAM.
- 🎯 **Full Hardware Customization:** Fine-tune DPI stages, polling report rates, macro recordings, button remaps, and RGB lighting with interactive device schematics.

---

## Screenshots

<div align="center">
  <h3>AutoPilot — Automatic Game Profile Switching</h3>
  <img src="data/screenshots/autopilot.png" alt="Cheddar AutoPilot" width="85%">
  <p><em>Automatically detect running games, assign custom mouse profiles, and configure background autostart with a modern Libadwaita interface.</em></p>
  <br>

  <h3>Hardware Configuration & DPI Resolutions</h3>
  <img src="data/screenshots/resolutions.png" alt="Cheddar Resolutions and Mouse Setup" width="85%">
  <p><em>Fine-tune sensitivity levels, switch active DPI presets, and remap buttons with interactive real-time mouse SVG visualization.</em></p>
</div>

---

## Features

- **Per-Game Profile Switching:** Map any game to a custom profile. Cheddar applies it when the game launches and reverts to your default profile when it closes.
- **Focus-Aware (Alt-Tab Follows You):** When running multiple games or alt-tabbing to your browser, Cheddar instantly gives priority to the focused window.
- **Full Wine / Proton / UMU & Native Support:** Seamlessly detects Windows games running under Proton/Wine (including Battle.net, Steam, Lutris, Heroic, and Faugus Launcher), not just native Linux executables.
- **Automated Game Library Indexing:** The rule editor automatically scans and displays your installed games with high-resolution artwork—no guesswork or manual binary paths required.
- **Unlimited Software Profiles:** Store hundreds of named profiles on your disk; Cheddar uses an onboard scratch slot to flash them to the mouse seamlessly.
- **Silent Background Daemon & Tray:** Runs quietly in the background via systemd user service or system tray, keeping profiles switching without leaving any window open.

---

## Installation

> [!IMPORTANT]
> **Why native installation?**  
> Cheddar's core engine (**AutoPilot**) monitors active game processes via `/proc` and tracks focused game windows. Sandboxed container formats like **Flatpak strictly isolate `/proc`** by design, which breaks automatic per-game switching.  
> Installing natively takes less than 30 seconds and ensures **100% of features work out of the box**.

### Requirements

- `ratbagd` / `libratbag` (0.18 or newer)
- GTK 3 & PyGObject
- Python 3 with modules `lxml`, `evdev`, `cairo`, `gi`
- `xprop` (*optional but recommended* for focus-based switching under X11)

---

### Arch Linux / CachyOS / Manjaro

```sh
# 1. Install dependencies
sudo pacman -S --needed meson ninja libratbag gtk3 python-gobject \
                        python-lxml python-evdev python-cairo xorg-xprop

# 2. Clone the repository and install
git clone https://github.com/Rilorca/cheddar.git
cd cheddar
meson setup builddir --prefix=/usr
ninja -C builddir
sudo ninja -C builddir install

# 3. Enable and start the ratbagd mouse daemon
sudo systemctl enable --now ratbagd
```

*(Optional: To install for your user only without `sudo`, replace `--prefix=/usr` with `--prefix=$HOME/.local` and run `ninja -C builddir install`).*

---

### Debian / Ubuntu / Linux Mint / Pop!_OS

```sh
# 1. Install dependencies
sudo apt update
sudo apt install meson ninja-build ratbagd gir1.2-gtk-3.0 python3-gi \
                 python3-lxml python3-evdev python3-cairo x11-utils

# 2. Clone the repository and install
git clone https://github.com/Rilorca/cheddar.git
cd cheddar
meson setup builddir --prefix=/usr
ninja -C builddir
sudo ninja -C builddir install

# 3. Enable and start ratbagd
sudo systemctl enable --now ratbagd
```

---

### Fedora / Nobara / RHEL

```sh
# 1. Install dependencies
sudo dnf install meson ninja-build libratbag-ratbagd gtk3 python3-gobject \
                 python3-lxml python3-evdev python3-cairo xprop

# 2. Clone the repository and install
git clone https://github.com/Rilorca/cheddar.git
cd cheddar
meson setup builddir --prefix=/usr
ninja -C builddir
sudo ninja -C builddir install

# 3. Enable and start ratbagd
sudo systemctl enable --now ratbagd
```

After installing, launch **Cheddar** from your application menu or run `cheddar` in a terminal.

---

## How It Works

### 1. Process & Window Detection (AutoPilot Engine)
Cheddar watches running processes via `/proc` with virtually zero CPU overhead (no root privileges required). For Proton and Wine games, it reads the game's actual Windows-style executable and command line from the process environment rather than just the generic Wine loader. When `xprop` is available, it also inspects the active window ID to give priority to whichever game is currently focused on your screen.

### 2. Overcoming Mouse Hardware Memory Limits
Most gaming mice only have 3 to 5 onboard profile slots in physical flash memory (e.g. Logitech G600 has 3). Cheddar bypasses this limitation by storing unlimited custom profiles in `~/.config/cheddar/autopilot_profiles.json`. When a game starts, Cheddar dynamically flashes that game's profile into a dedicated onboard "scratch slot" (by default the last slot) and activates it immediately. Your other onboard profiles remain untouched.

### 3. Background Switching
To enable background profile switching:
1. **Via UI:** Open Cheddar $\rightarrow$ **AutoPilot** tab $\rightarrow$ toggle **Enable AutoPilot**. You can also check **Start at login** to keep Cheddar in your system tray upon boot.
2. **Via systemd user service (Optional):**
   ```sh
   systemctl --user enable --now cheddar-autopilot
   ```
   Check daemon activity anytime:
   ```sh
   journalctl --user -u cheddar-autopilot -f
   ```

### 4. Configuration Storage
All your settings and rules are stored in `~/.config/cheddar/`:
- `autopilot.json` — rules, default profile, switch states.
- `autopilot_profiles.json` — your custom named profile library.
- `backups/` — automatic backups of your mouse's original onboard profiles.

---

## Troubleshooting

- **"Cannot find any devices" / Welcome screen:** `ratbagd` isn't running or your mouse needs re-enumeration. Run `sudo systemctl start ratbagd` and replug the mouse.
- **Solaar conflict (Logitech wireless mice):** If [Solaar](https://pwr-solaar.github.io/Solaar/) is running when `ratbagd` starts, it may claim the device first, causing `ratbagd` to fail reading profiles. Stop Solaar (`killall solaar`), restart ratbagd (`sudo systemctl restart ratbagd`), and replug your mouse.
- **Game not detected:** Check the daemon log while launching your game:
  ```sh
  journalctl --user -u cheddar-autopilot -f
  ```
  Then add a rule using the exact executable name shown in the log.

---

## Contributing & Development

To test and develop without installing system-wide:

```sh
meson setup builddir
ninja -C builddir
./builddir/cheddar.devel
```

Code formatting and linting:
```sh
meson test -C builddir
```

---

## License

GPL-2.0-or-later, same as upstream Piper. See [COPYING](COPYING).  
Cheddar is built on the foundation of [Piper](https://github.com/libratbag/piper) by the libratbag project.
