# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilot_games.py — part of Cheddar AutoPilot fork
#
# Discovers installed games so the rule dialog can offer a picker (the way
# G HUB lists installed titles) instead of making the user type executable
# names by hand. Best-effort scanners per launcher; everything degrades to an
# empty list, never an exception.

import json
import logging
import os
import re
from typing import Dict, List, NamedTuple, Optional

logger = logging.getLogger(__name__)

_STEAM_ROOTS = (
    "~/.local/share/Steam",
    "~/.steam/steam",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam",  # flatpak
)

# Steam "games" that are really runtimes/tools.
_STEAM_TOOL_PREFIXES = (
    "proton",
    "steamworks",
    "steam linux runtime",
    "steamvr",
)

# Executables that are never the game itself.
_EXE_BLACKLIST = re.compile(
    r"crash|report|unins|setup|redist|vc_redist|dxsetup|dotnet|handler"
    r"|installscript|eac|easyanticheat|touchup|activation",
    re.IGNORECASE,
)

# Directories not worth descending into.
_DIR_BLACKLIST = {
    "_commonredist",
    "commonredist",
    "redist",
    "directx",
    "dotnet",
    "mono",
    "monobleedingedge",
    "errorreporting",
    "vcredist",
    "support",
    "soundtrack",
}

_WALK_MAX_DEPTH = 3


class Game(NamedTuple):
    name: str  # display name ("Overwatch®")
    exe: str  # process basename for the rule ("overwatch.exe")
    source: str  # launcher it came from ("Steam")
    icon: Optional[str] = None  # path to a small icon image, if one was found


def _steam_icon(steam_root: str, appid: str) -> Optional[str]:
    """Path to the game's small icon in Steam's library cache, if any.

    Older Steam clients store it as librarycache/{appid}_icon.jpg; newer ones
    keep hash-named files inside librarycache/{appid}/ where the icon is the
    small square image among posters and heroes. GdkPixbuf.get_file_info
    reads only the header, so probing sizes is cheap.
    """
    cache = os.path.join(steam_root, "appcache", "librarycache")
    legacy = os.path.join(cache, f"{appid}_icon.jpg")
    if os.path.isfile(legacy):
        return legacy
    appdir = os.path.join(cache, appid)
    try:
        entries = os.listdir(appdir)
    except OSError:
        return None
    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf
    except (ImportError, ValueError):  # headless callers don't need icons
        return None
    best: Optional[str] = None
    best_size = 0
    for fname in entries:
        path = os.path.join(appdir, fname)
        info = GdkPixbuf.Pixbuf.get_file_info(path)
        fmt, width, height = info if isinstance(info, tuple) else (info, 0, 0)
        if fmt is None or width != height or not 16 <= width <= 128:
            continue
        if width > best_size:
            best, best_size = path, width
    return best


def _normalize(s: str) -> str:
    """Lowercase alphanumerics only, for fuzzy name comparison."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


_ARCH_SUFFIX = re.compile(
    r"[-_]?(?:x86_64|x86|x64|64|32|win64|win32)+$", re.IGNORECASE
)


def _generate_hints(hint_names: List[str]) -> List[str]:
    """Generate normalized hint strings, including acronyms for multi-word titles."""
    hints = set()
    for h in hint_names:
        if not h:
            continue
        norm = _normalize(h)
        if norm:
            hints.add(norm)
        # Acronym if multiple words (e.g. "World of Warcraft" -> "wow", "Heroes of the Storm" -> "hots")
        words = re.findall(r"[a-zA-Z0-9]+", h)
        if len(words) > 1:
            acronym = _normalize("".join(w[0] for w in words))
            if len(acronym) >= 2:
                hints.add(acronym)
    return list(hints)


def _find_game_exe(install_dir: str, hint_names: List[str]) -> Optional[str]:
    """Pick the most plausible game executable inside install_dir.

    Considers Windows .exe files and native Linux executables up to
    _WALK_MAX_DEPTH deep, skipping known helper/redist noise. Ranking:
    name similarity to the game first, real game binaries over launcher stubs,
    then shallower path, then larger file.
    """
    hints = _generate_hints(hint_names)
    candidates = []  # (score, is_not_launcher, -depth, size, basename)
    base_depth = install_dir.rstrip("/").count("/")
    for root, dirs, files in os.walk(install_dir):
        depth = root.rstrip("/").count("/") - base_depth
        if depth >= _WALK_MAX_DEPTH:
            dirs.clear()
        dirs[:] = [d for d in dirs if d.lower() not in _DIR_BLACKLIST]
        for fname in files:
            path = os.path.join(root, fname)
            # Windows games: any .exe. Native games: executable file whose
            # name has no extension besides an optional .x86_64 suffix
            # (filters .so/.dll/.txt while keeping "Game" and "Game.x86_64").
            if not fname.lower().endswith(".exe") and (
                not os.access(path, os.X_OK) or "." in fname.removesuffix(".x86_64")
            ):
                continue
            if _EXE_BLACKLIST.search(fname):
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size < 100 * 1024:  # tiny helpers/scripts
                continue
            stem = _normalize(fname.rsplit(".", 1)[0] if "." in fname else fname)
            stem_no_arch = _ARCH_SUFFIX.sub("", stem)
            is_not_launcher = 0 if "launcher" in fname.lower() else 1
            score = 0
            for h in hints:
                if stem == h or stem_no_arch == h:
                    score = 3
                    break
                if h and (stem.startswith(h) or h.startswith(stem) or stem_no_arch.startswith(h)):
                    score = max(score, 2)
                elif h and (h in stem or stem in h):
                    score = max(score, 1)
            candidates.append((score, is_not_launcher, -depth, size, fname))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][4]


# ── Steam ──────────────────────────────────────────────────────────────────────


def _steam_library_paths(steam_root: str) -> List[str]:
    vdf = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
    paths = []
    try:
        with open(vdf, encoding="utf-8", errors="replace") as f:
            for m in re.finditer(r'"path"\s+"([^"]+)"', f.read()):
                paths.append(m.group(1))
    except OSError:
        pass
    if not paths and os.path.isdir(os.path.join(steam_root, "steamapps")):
        paths.append(steam_root)
    return paths


def _scan_steam() -> List[Game]:
    games: List[Game] = []
    seen_roots = set()
    for root in _STEAM_ROOTS:
        root = os.path.realpath(os.path.expanduser(root))
        if root in seen_roots or not os.path.isdir(root):
            continue
        seen_roots.add(root)
        for lib in _steam_library_paths(root):
            steamapps = os.path.join(lib, "steamapps")
            try:
                manifests = [
                    f
                    for f in os.listdir(steamapps)
                    if f.startswith("appmanifest_") and f.endswith(".acf")
                ]
            except OSError:
                continue
            for mf in manifests:
                try:
                    with open(
                        os.path.join(steamapps, mf),
                        encoding="utf-8",
                        errors="replace",
                    ) as f:
                        data = f.read()
                except OSError:
                    continue
                name_m = re.search(r'"name"\s+"([^"]+)"', data)
                dir_m = re.search(r'"installdir"\s+"([^"]+)"', data)
                if not name_m or not dir_m:
                    continue
                name = name_m.group(1)
                if name.lower().startswith(_STEAM_TOOL_PREFIXES):
                    continue
                install_dir = os.path.join(steamapps, "common", dir_m.group(1))
                if not os.path.isdir(install_dir):
                    continue
                exe = _find_game_exe(install_dir, [dir_m.group(1), name])
                if exe:
                    appid = mf[len("appmanifest_") : -len(".acf")]
                    games.append(
                        Game(name, exe.lower(), "Steam", _steam_icon(root, appid))
                    )
    return games


# ── Lutris ─────────────────────────────────────────────────────────────────────


def _scan_lutris() -> List[Game]:
    games: List[Game] = []
    cfg_dir = os.path.expanduser("~/.config/lutris/games")
    try:
        ymls = os.listdir(cfg_dir)
    except OSError:
        return games
    for fname in ymls:
        if not fname.endswith(".yml"):
            continue
        try:
            with open(
                os.path.join(cfg_dir, fname), encoding="utf-8", errors="replace"
            ) as f:
                data = f.read()
        except OSError:
            continue
        # Crude but dependency-free: grab the exe: line from the game section.
        exe_m = re.search(r"^\s*exe:\s*(.+)$", data, re.MULTILINE)
        if not exe_m:
            continue
        exe = os.path.basename(exe_m.group(1).strip().strip("'\""))
        # lutris config files are "<slug>-<timestamp>.yml"
        slug = re.sub(r"-\d+$", "", fname[:-4])
        name = slug.replace("-", " ").title()
        icon = os.path.expanduser(
            f"~/.local/share/icons/hicolor/128x128/apps/lutris_{slug}.png"
        )
        games.append(
            Game(name, exe.lower(), "Lutris", icon if os.path.isfile(icon) else None)
        )
    return games


# ── Heroic (Epic via legendary, GOG, sideloaded) ───────────────────────────────


def _heroic_json(path: str) -> Optional[Dict]:
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _scan_heroic() -> List[Game]:
    games: List[Game] = []
    # Epic (legendary backend)
    data = _heroic_json("~/.config/legendary/installed.json")
    if isinstance(data, dict):
        for item in data.values():
            title, exe = item.get("title"), item.get("executable")
            if title and exe:
                games.append(Game(title, os.path.basename(exe).lower(), "Heroic"))
    # GOG
    data = _heroic_json("~/.config/heroic/gog_store/installed.json")
    installed = data.get("installed", []) if isinstance(data, dict) else []
    for item in installed:
        path = item.get("install_path")
        if not path or not os.path.isdir(path):
            continue
        hint = os.path.basename(path.rstrip("/"))
        exe = _find_game_exe(path, [hint])
        if exe:
            games.append(Game(hint, exe.lower(), "Heroic"))
    # Sideloaded apps
    data = _heroic_json("~/.config/heroic/sideload_apps/library.json")
    apps = data.get("games", []) if isinstance(data, dict) else []
    for item in apps:
        title = item.get("title")
        exe = (item.get("install", {}) or {}).get("executable")
        if title and exe:
            games.append(Game(title, os.path.basename(exe).lower(), "Heroic"))
    return games


# ── Faugus Launcher (UMU-based runner / Flatpak & native) ──────────────────────

_FAUGUS_ROOTS = (
    "~/.var/app/io.github.Faugus.faugus-launcher/data/faugus-launcher",
    "~/.var/app/io.github.Faugus.faugus-launcher/config/faugus-launcher",
    "~/.local/share/faugus-launcher",
    "~/.config/faugus-launcher",
)

_WINDOWS_SYS_DIRS = {
    "common files",
    "internet explorer",
    "windows media player",
    "windows nt",
    "windows mail",
    "windows defender",
    "msbuild",
    "reference assemblies",
    "windows photo viewer",
    "uninstall information",
    "installshield installation information",
}


def _find_proton_shortcut_icon(prefix: str, icon_name: Optional[str]) -> Optional[str]:
    """Find the highest resolution icon for a Proton/UMU shortcut."""
    if not icon_name:
        return None
    if os.path.isabs(icon_name) and os.path.isfile(icon_name):
        return icon_name
    icons_dir = os.path.join(prefix, "drive_c", "proton_shortcuts", "icons")
    for sz in ("256x256", "128x128", "96x96", "64x64", "48x48", "32x32", "16x16"):
        p = os.path.join(icons_dir, sz, "apps", f"{icon_name}.png")
        if os.path.isfile(p):
            return p
    return None


def _scan_faugus() -> List[Game]:
    games: List[Game] = []
    seen_exes = set()
    seen_prefixes = set()

    for root_path in _FAUGUS_ROOTS:
        full_root = os.path.realpath(os.path.expanduser(root_path))
        gj = os.path.join(full_root, "games.json")
        if not os.path.isfile(gj):
            continue
        try:
            with open(gj, "r", encoding="utf-8", errors="replace") as f:
                entries = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            title = entry.get("title")
            path = entry.get("path")
            prefix = entry.get("prefix")
            icon = entry.get("icon")
            if icon and not os.path.isfile(icon):
                icon = None

            # 1. Games installed inside the Wine prefix (e.g. Battle.net library)
            if prefix and prefix not in seen_prefixes and os.path.isdir(prefix):
                seen_prefixes.add(prefix)

                # A. Inspect proton_shortcuts created by UMU/Proton
                shortcuts_dir = os.path.join(prefix, "drive_c", "proton_shortcuts")
                sc_installed_paths = set()
                if os.path.isdir(shortcuts_dir):
                    try:
                        sc_files = os.listdir(shortcuts_dir)
                    except OSError:
                        sc_files = []
                    for sc in sc_files:
                        if not sc.endswith(".desktop"):
                            continue
                        sc_path = os.path.join(shortcuts_dir, sc)
                        try:
                            with open(
                                sc_path, "r", encoding="utf-8", errors="replace"
                            ) as sf:
                                content = sf.read()
                        except OSError:
                            continue
                        nm = re.search(r"^Name=(.+)$", content, re.MULTILINE)
                        pm = re.search(r"^Path=(.+)$", content, re.MULTILINE)
                        im = re.search(r"^Icon=(.+)$", content, re.MULTILINE)
                        game_name = nm.group(1).strip() if nm else sc[:-8]
                        install_path = pm.group(1).strip() if pm else None
                        shortcut_icon = (
                            _find_proton_shortcut_icon(prefix, im.group(1).strip())
                            if im
                            else None
                        ) or icon

                        if install_path and os.path.isdir(install_path):
                            sc_installed_paths.add(os.path.realpath(install_path))
                            exe = _find_game_exe(
                                install_path,
                                [game_name, os.path.basename(install_path)],
                            )
                            if exe:
                                exe_lower = exe.lower()
                                games.append(
                                    Game(game_name, exe_lower, "Faugus", shortcut_icon)
                                )
                                seen_exes.add(exe_lower)

                # B. Inspect Program Files directories in case shortcuts weren't generated
                for pf_name in ("Program Files (x86)", "Program Files"):
                    pf_dir = os.path.join(prefix, "drive_c", pf_name)
                    if not os.path.isdir(pf_dir):
                        continue
                    try:
                        subdirs = os.listdir(pf_dir)
                    except OSError:
                        continue
                    for sd in subdirs:
                        if sd.lower() in _WINDOWS_SYS_DIRS:
                            continue
                        game_dir = os.path.join(pf_dir, sd)
                        if (
                            not os.path.isdir(game_dir)
                            or os.path.realpath(game_dir) in sc_installed_paths
                        ):
                            continue
                        exe = _find_game_exe(game_dir, [sd])
                        if exe and exe.lower() not in seen_exes:
                            exe_lower = exe.lower()
                            games.append(Game(sd, exe_lower, "Faugus", None))
                            seen_exes.add(exe_lower)

            # 2. Add the configured Faugus entry itself (e.g. standalone game or launcher)
            if title and path:
                base_exe = os.path.basename(path).lower()
                if base_exe and base_exe not in seen_exes:
                    games.append(Game(title, base_exe, "Faugus", icon))
                    seen_exes.add(base_exe)

    return games


# ── Public API ─────────────────────────────────────────────────────────────────


def installed_games() -> List[Game]:
    """All detected installed games, deduplicated by exe, sorted by name."""
    games: List[Game] = []
    for scanner in (_scan_steam, _scan_lutris, _scan_heroic, _scan_faugus):
        try:
            games.extend(scanner())
        except Exception as e:
            logger.warning("game scanner %s failed: %s", scanner.__name__, e)
    dedup: Dict[str, Game] = {}
    for g in games:
        dedup.setdefault(g.exe, g)
    return sorted(dedup.values(), key=lambda g: g.name.lower())

