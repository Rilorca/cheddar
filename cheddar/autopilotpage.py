# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilotpage.py — part of Cheddar AutoPilot fork
#
# Adds an "AutoPilot" tab to Cheddar's per-device stack switcher.
# The page lets users:
#   • Map game executables to profiles (Add / Edit / Delete rules)
#   • Choose a default profile (used when no mapped game is running)
#   • Start / stop the background process watcher
#
# Design: pure-Python GTK3 widget — no extra .ui file required.
# Follows the same style conventions as Cheddar's other pages.

import threading
from gettext import gettext as _
from typing import Dict, List, Optional

from . import autostart
from . import autopilot_profiles as ap
from .autopilot_config import load as cfg_load, save as cfg_save
from .autopilot_games import installed_games
from .autopilot_watcher import AutoPilotWatcher, RuleTarget
from .ratbagd import RatbagdDevice, RatbagdProfile

import math
import cairo
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa

try:
    gi.require_version("Notify", "0.7")
    from gi.repository import Notify
    if not Notify.is_initted():
        Notify.init("io.github.rilorca.Cheddar")
except Exception:
    Notify = None


def _load_game_icon(path: Optional[str], size: int = 36) -> Optional[GdkPixbuf.Pixbuf]:
    """Load a game icon as a rounded squircle of `size` px; themed fallback."""
    if path:
        try:
            src = GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
            return _rounded(src, size)
        except GLib.Error:
            pass
    try:
        fallback = Gtk.IconTheme.get_default().load_icon(
            "applications-games-symbolic", max(16, size - 12), 0
        )
        if fallback:
            return _rounded(fallback, size)
    except GLib.Error:
        pass
    return None


def _rounded(pixbuf: GdkPixbuf.Pixbuf, size: int) -> GdkPixbuf.Pixbuf:
    """Clip a pixbuf to a squircle with rounded corners (Libadwaita style)."""
    radius = max(6, size // 4)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)
    cr.new_sub_path()
    cr.arc(size - radius, radius, radius, -1.5708, 0)
    cr.arc(size - radius, size - radius, radius, 0, 1.5708)
    cr.arc(radius, size - radius, radius, 1.5708, 3.1416)
    cr.arc(radius, radius, radius, 3.1416, 4.7124)
    cr.close_path()
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.06)
    cr.fill_preserve()
    cr.clip()
    # Center the (possibly non-square) scaled icon inside the square
    Gdk.cairo_set_source_pixbuf(
        cr,
        pixbuf,
        (size - pixbuf.get_width()) / 2,
        (size - pixbuf.get_height()) / 2,
    )
    cr.paint()
    return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)


def _profile_label(profile: RatbagdProfile) -> str:
    """The exact name the profile switcher (ProfileRow) shows for a profile,
    so AutoPilot never presents a numbering of its own."""
    return profile.name or f"Profile {profile.index}"


# ─── Helper: Rule-editor dialog ───────────────────────────────────────────────


class _RuleDialog(Gtk.Dialog):
    """Modal dialog to add or edit a single game→profile rule."""

    def __init__(
        self,
        parent: Gtk.Widget,
        profiles: List[RatbagdProfile],
        exe: str = "",
        profile_index: int = 0,
        title: str = "",
        default_profile: Optional[int] = None,
    ) -> None:
        super().__init__(
            title=title or _("Add Rule"),
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
            use_header_bar=True,
        )
        self.set_default_size(440, -1)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        ok_btn = self.add_button(_("_Save"), Gtk.ResponseType.OK)
        ok_btn.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)

        self._default_profile = default_profile

        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=10,
            border_width=18,
        )
        self.get_content_area().add(grid)

        # ── Installed-game picker (G HUB style) ───────────────────────────────
        lbl_game = Gtk.Label(label=_("Installed game"), xalign=0)
        lbl_game.get_style_context().add_class("dim-label")
        grid.attach(lbl_game, 0, 0, 1, 1)

        self._games = installed_games()
        # id, icon, label — a plain ComboBoxText can't render the game icons
        store = Gtk.ListStore(str, GdkPixbuf.Pixbuf, str)
        self._game_combo = Gtk.ComboBox(model=store, hexpand=True)
        self._game_combo.set_id_column(0)
        icon_cell = Gtk.CellRendererPixbuf(xpad=4)
        self._game_combo.pack_start(icon_cell, False)
        self._game_combo.add_attribute(icon_cell, "pixbuf", 1)
        text_cell = Gtk.CellRendererText()
        self._game_combo.pack_start(text_cell, True)
        self._game_combo.add_attribute(text_cell, "text", 2)
        if self._games:
            store.append(["", None, _("Choose a game…")])
            for i, game in enumerate(self._games):
                store.append(
                    [
                        str(i),
                        _load_game_icon(game.icon),
                        f"{game.name}  ({game.source})",
                    ]
                )
            self._game_combo.set_active_id("")
            self._game_combo.connect("changed", self._on_game_selected)
        else:
            store.append(["", None, _("No games detected")])
            self._game_combo.set_active_id("")
            self._game_combo.set_sensitive(False)
        grid.attach(self._game_combo, 1, 0, 1, 1)

        # ── Executable name ───────────────────────────────────────────────────
        lbl_exe = Gtk.Label(label=_("Game executable"), xalign=0)
        lbl_exe.get_style_context().add_class("dim-label")
        grid.attach(lbl_exe, 0, 1, 1, 1)

        self._exe_entry = Gtk.Entry(
            hexpand=True,
            placeholder_text=_("e.g.  cs2   or   cyberpunk2077.exe"),
            activates_default=True,
            text=exe,
        )
        grid.attach(self._exe_entry, 1, 1, 1, 1)

        hint = Gtk.Label(xalign=0)
        hint.set_markup(
            '<span size="small" foreground="grey">'
            + _("Basename only, case-insensitive. Extension optional.")
            + "</span>"
        )
        grid.attach(hint, 1, 2, 1, 1)

        # ── Profile picker ────────────────────────────────────────────────────
        lbl_p = Gtk.Label(label=_("Switch to profile"), xalign=0)
        lbl_p.get_style_context().add_class("dim-label")
        grid.attach(lbl_p, 0, 3, 1, 1)

        self._profile_combo = Gtk.ComboBoxText(hexpand=True)
        for p in profiles:
            self._profile_combo.append(str(p.index), _profile_label(p))
        # The user's named profiles list right after the onboard slots, with
        # no technical distinction — G HUB style: the syncing is our problem.
        for name in sorted(ap.load_store()):
            self._profile_combo.append(ap.SW_PREFIX + name, name)
        self._profile_combo.set_active_id(str(profile_index))
        if self._profile_combo.get_active_id() is None:
            self._profile_combo.set_active(0)
        self._profile_combo.connect("changed", self._update_warning)
        grid.attach(self._profile_combo, 1, 3, 1, 1)

        # Warn when the rule is a no-op (same profile as the default).
        self._warning = Gtk.Label(xalign=0, wrap=True, max_width_chars=44)
        grid.attach(self._warning, 1, 4, 1, 1)

        grid.show_all()
        self._update_warning()

    def _on_game_selected(self, combo: Gtk.ComboBoxText) -> None:
        aid = combo.get_active_id()
        if aid:
            self._exe_entry.set_text(self._games[int(aid)].exe)

    def _update_warning(self, *_args) -> None:
        if self._default_profile is not None and self.target == self._default_profile:
            self._warning.set_markup(
                '<span size="small" foreground="orange">⚠ '
                + _(
                    "This is already the default profile — the rule "
                    "won't change anything."
                )
                + "</span>"
            )
        else:
            self._warning.set_markup("")

    @property
    def exe(self) -> str:
        return self._exe_entry.get_text().strip().lower()

    @property
    def target(self) -> RuleTarget:
        """The chosen rule target: onboard profile index (int) or a
        software profile reference ("sw:<name>")."""
        aid = self._profile_combo.get_active_id()
        if aid is None:
            return 0
        return aid if aid.startswith(ap.SW_PREFIX) else int(aid)


# ─── Main page widget ──────────────────────────────────────────────────────────


class AutoPilotPage(Gtk.Box):
    """
    The AutoPilot tab shown inside Cheddar's per-device stack-switcher.

    Integrates with MousePerspective exactly like ResolutionsPage or
    AdvancedPage: constructed with (device, profile) and added to the
    GtkStack via stack.add_titled().

    One instance is shared across profile switches (unlike other pages)
    because the watcher is device-wide, not per-profile.
    """

    def __init__(self, device: RatbagdDevice) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        self._device = device
        self._config: Dict = cfg_load()
        self._watcher: Optional[AutoPilotWatcher] = None
        self._editing_name: Optional[str] = None

        # Map rule exes to installed games so rule rows can show the game's
        # title and icon (keyed with and without the .exe suffix).
        self._game_by_exe: Dict[str, object] = {}
        for game in installed_games():
            self._game_by_exe.setdefault(game.exe, game)
            self._game_by_exe.setdefault(game.exe.removesuffix(".exe"), game)
            self._game_by_exe.setdefault(game.exe.lower(), game)
            self._game_by_exe.setdefault(game.exe.lower().removesuffix(".exe"), game)
            if " " in game.exe:
                self._game_by_exe.setdefault(game.exe.lower().replace(" ", ""), game)
                self._game_by_exe.setdefault(
                    game.exe.lower().removesuffix(".exe").replace(" ", ""), game
                )

        self._build_ui()

        # Auto-restart watcher if it was enabled last session
        if self._config.get("enabled", False):
            GLib.idle_add(self._start_watcher)

        self.show_all()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        self.pack_start(outer, True, True, 0)

        # Center clamp container (matches GNOME Libadwaita AdwClamp)
        clamp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        clamp_box.set_halign(Gtk.Align.CENTER)
        clamp_box.set_hexpand(True)
        outer.add(clamp_box)

        col = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
            border_width=24,
            width_request=680,
        )
        clamp_box.pack_start(col, True, True, 0)

        # ── Master status hero card ───────────────────────────────────────────
        status_card = Gtk.Frame()
        status_card.get_style_context().add_class("hero-card")
        status_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=16, border_width=18
        )
        status_card.add(status_row)

        self._status_indicator = Gtk.DrawingArea()
        self._status_indicator.set_size_request(28, 28)
        self._status_indicator.set_valign(Gtk.Align.CENTER)
        self._status_indicator.connect("draw", self._on_draw_status_indicator)
        status_row.pack_start(self._status_indicator, False, False, 2)

        status_text = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True, valign=Gtk.Align.CENTER
        )
        title = Gtk.Label(xalign=0)
        title.set_markup(
            '<span size="large" weight="bold">'
            + _("Automatic profile switching")
            + "</span>"
        )
        status_text.pack_start(title, False, False, 0)
        self._status_label = Gtk.Label(xalign=0)
        self._update_status_label()
        status_text.pack_start(self._status_label, False, False, 0)
        status_row.pack_start(status_text, True, True, 0)

        self._toggle = Gtk.Switch(valign=Gtk.Align.CENTER)
        self._toggle.set_active(self._config.get("enabled", False))
        self._toggle.connect("notify::active", self._on_toggle_changed)
        status_row.pack_start(self._toggle, False, False, 0)
        col.pack_start(status_card, False, False, 0)

        # ── Games header ──────────────────────────────────────────────────────
        games_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=6
        )
        gh_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
        gh_title = Gtk.Label(xalign=0)
        gh_title.set_markup(f'<span size="medium" weight="bold">{_("Your games")}</span>')
        gh_text.pack_start(gh_title, False, False, 0)
        gh_sub = Gtk.Label(xalign=0)
        gh_sub.set_markup(
            '<span size="small" foreground="grey">'
            + _(
                "When a game starts, its profile is loaded onto the mouse automatically."
            )
            + "</span>"
        )
        gh_text.pack_start(gh_sub, False, False, 0)
        games_header.pack_start(gh_text, True, True, 0)

        self._add_btn = Gtk.Button(label=_("Add game"))
        self._add_btn.set_image(
            Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        )
        self._add_btn.set_always_show_image(True)
        self._add_btn.get_style_context().add_class("suggested-action")
        self._add_btn.set_valign(Gtk.Align.CENTER)
        self._add_btn.connect("clicked", self._on_add_rule)
        games_header.pack_start(self._add_btn, False, False, 0)
        col.pack_start(games_header, False, False, 0)

        # ── Games list (Boxed List) ───────────────────────────────────────────
        rules_card = Gtk.Frame()
        rules_card.get_style_context().add_class("card")
        self._rules_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._rules_box.get_style_context().add_class("boxed-list")
        self._rules_box.set_header_func(self._rules_header_func)
        rules_card.add(self._rules_box)
        col.pack_start(rules_card, False, False, 0)
        self._refresh_rules()

        # ── System Settings Section (Boxed List matching mockup) ──────────────
        sys_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=8
        )
        sys_title = Gtk.Label(xalign=0)
        sys_title.set_markup(f'<span size="medium" weight="bold">{_("System Settings")}</span>')
        sys_header.pack_start(sys_title, True, True, 0)
        col.pack_start(sys_header, False, False, 0)

        sys_card = Gtk.Frame()
        sys_card.get_style_context().add_class("card")
        self._sys_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._sys_box.get_style_context().add_class("boxed-list")
        self._sys_box.set_header_func(self._rules_header_func)
        sys_card.add(self._sys_box)
        col.pack_start(sys_card, False, False, 0)

        # Row 1: Launch on startup
        row_startup = Gtk.ListBoxRow()
        row_startup_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14, border_width=14)
        s_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True, valign=Gtk.Align.CENTER)
        s_title = Gtk.Label(xalign=0)
        s_title.set_markup(f"<b>{GLib.markup_escape_text(_('Launch on system startup'))}</b>")
        s_text.pack_start(s_title, False, False, 0)
        s_sub = Gtk.Label(xalign=0)
        s_sub.set_markup(
            '<span size="small" foreground="grey">'
            + _("Start Cheddar in the background tray when you log in")
            + "</span>"
        )
        s_text.pack_start(s_sub, False, False, 0)
        row_startup_box.pack_start(s_text, True, True, 0)

        self._startup_toggle = Gtk.Switch(valign=Gtk.Align.CENTER)
        self._startup_toggle.set_active(autostart.is_autostart_enabled())
        self._startup_toggle.connect("notify::active", self._on_startup_toggled)
        row_startup_box.pack_start(self._startup_toggle, False, False, 0)
        row_startup.add(row_startup_box)
        self._sys_box.add(row_startup)

        # Row 2: Switch notifications
        row_notif = Gtk.ListBoxRow()
        row_notif_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14, border_width=14)
        n_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True, valign=Gtk.Align.CENTER)
        n_title = Gtk.Label(xalign=0)
        n_title.set_markup(f"<b>{GLib.markup_escape_text(_('Switch notifications'))}</b>")
        n_text.pack_start(n_title, False, False, 0)
        n_sub = Gtk.Label(xalign=0)
        n_sub.set_markup(
            '<span size="small" foreground="grey">'
            + _("Show a system notification when switching profiles")
            + "</span>"
        )
        n_text.pack_start(n_sub, False, False, 0)
        row_notif_box.pack_start(n_text, True, True, 0)

        self._notifications_toggle = Gtk.Switch(valign=Gtk.Align.CENTER)
        self._notifications_toggle.set_active(self._config.get("notifications_enabled", True))
        self._notifications_toggle.connect("notify::active", self._on_notifications_toggled)
        row_notif_box.pack_start(self._notifications_toggle, False, False, 0)
        row_notif.add(row_notif_box)
        self._sys_box.add(row_notif)

        # User-created profiles are managed from the profile switcher popover
        # (top-left), where they list alongside the onboard ones — see
        # MousePerspective. This view only maps games to profiles.

    def _on_startup_toggled(self, switch: Gtk.Switch, _pspec) -> None:
        autostart.set_autostart_enabled(switch.get_active())

    def _rules_header_func(self, row, before):
        """Add a separator between rows (Cheddar style)."""
        if before is not None and row.get_header() is None:
            row.set_header(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    # ── Rules list ─────────────────────────────────────────────────────────────

    def _refresh_rules(self) -> None:
        for child in self._rules_box.get_children():
            self._rules_box.remove(child)

        rules: Dict[str, int] = self._config.get("rules", {})

        if not rules:
            placeholder = Gtk.ListBoxRow(activatable=False, selectable=False)
            placeholder_lbl = Gtk.Label(
                label=_('No rules yet. Click "+ Add rule" to get started.'),
                margin_top=32,
                margin_bottom=32,
            )
            placeholder_lbl.get_style_context().add_class("dim-label")
            placeholder.add(placeholder_lbl)
            self._rules_box.add(placeholder)
        else:
            for exe, profile_idx in sorted(rules.items()):
                row = self._make_rule_row(exe, profile_idx)
                self._rules_box.add(row)

        self._rules_box.show_all()

    def _make_rule_row(self, exe: str, profile_idx: int) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow(activatable=False, selectable=False)
        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=14,
            border_width=10,
        )

        # Game icon: rounded 36px squircle
        game = (
            self._game_by_exe.get(exe)
            or self._game_by_exe.get(exe.lower())
            or self._game_by_exe.get(exe.lower().replace(" ", ""))
        )
        pixbuf = _load_game_icon(game.icon if game else None, size=36)
        if pixbuf is not None:
            icon = Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            icon = Gtk.Image.new_from_icon_name(
                "applications-games-symbolic", Gtk.IconSize.LARGE_TOOLBAR
            )
        box.pack_start(icon, False, False, 0)

        # Game details: Title and Subtitle
        details = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True, valign=Gtk.Align.CENTER
        )
        top_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        display = game.name if game else exe.removesuffix(".exe")
        name_lbl = Gtk.Label(xalign=0)
        name_lbl.set_markup(f"<b>{GLib.markup_escape_text(display)}</b>")
        top_line.pack_start(name_lbl, False, False, 0)

        if game and game.source:
            source_lbl = Gtk.Label(label=game.source)
            source_lbl.get_style_context().add_class("source-chip")
            if game.source.lower() == "steam":
                source_lbl.get_style_context().add_class("steam")
            top_line.pack_start(source_lbl, False, False, 0)
        details.pack_start(top_line, False, False, 0)

        meta_text = exe
        if game and game.source and game.source != "Steam":
            meta_text = f"{exe} • {game.source}"
        sub_lbl = Gtk.Label(xalign=0)
        sub_lbl.set_markup(f"<span size='small' foreground='grey'>{GLib.markup_escape_text(meta_text)}</span>")
        details.pack_start(sub_lbl, False, False, 0)
        box.pack_start(details, True, True, 0)

        # Interactive Profile Pill Combobox
        target_combo = Gtk.ComboBoxText(valign=Gtk.Align.CENTER)
        target_combo.get_style_context().add_class("profile-pill-combo")
        for p in self._device.profiles:
            target_combo.append(str(p.index), _profile_label(p))
        for name in sorted(ap.load_store()):
            target_combo.append(ap.SW_PREFIX + name, name)

        target_val = str(profile_idx)
        target_combo.set_active_id(target_val)
        target_combo.connect("changed", self._on_rule_combo_changed, exe)
        box.pack_start(target_combo, False, False, 6)

        # Delete button (clean flat circular with subtle hover red, NO huge red block)
        del_btn = Gtk.Button(relief=Gtk.ReliefStyle.NONE, valign=Gtk.Align.CENTER)
        del_btn.add(
            Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON)
        )
        del_btn.set_tooltip_text(_("Delete this rule"))
        del_btn.get_style_context().add_class("flat")
        del_btn.get_style_context().add_class("circular")
        del_btn.get_style_context().add_class("delete-row-btn")
        del_btn.connect("clicked", self._on_delete_rule, exe)
        box.pack_start(del_btn, False, False, 0)

        row.add(box)
        return row

    def _on_rule_combo_changed(self, combo: Gtk.ComboBoxText, exe: str) -> None:
        val = combo.get_active_id()
        if val is None:
            return
        target = val if val.startswith(ap.SW_PREFIX) else int(val)
        self._config.setdefault("rules", {})[exe] = target
        cfg_save(self._config)
        self._sync_watcher_rules()

    # ── Watcher control ────────────────────────────────────────────────────────

    def _start_watcher(self) -> None:
        if self._watcher and self._watcher.is_running():
            return
        rules = self._config.get("rules", {})
        default = self._config.get("default_profile", 0)
        self._watcher = AutoPilotWatcher(
            rules=rules,
            on_switch=self._on_watcher_switch,
            default_profile=default,
        )
        self._watcher.start()
        self._update_status_label()

    def _stop_watcher(self) -> None:
        if self._watcher:
            threading.Thread(target=self._watcher.stop, daemon=True).start()
            self._watcher = None
        self._update_status_label()

    # ── Public API for MousePerspective ────────────────────────────────────────

    @property
    def autopilot_enabled(self) -> bool:
        return bool(self._config.get("enabled", False))

    @property
    def scratch_slot(self) -> int:
        """The onboard slot AutoPilot reserves for named profiles."""
        return ap.scratch_slot_for(self._device, self._config)

    def connect_enabled_changed(self, callback) -> None:
        """Invoke callback whenever the AutoPilot toggle changes."""
        self._toggle.connect("notify::active", lambda *_: callback())

    # ── User profiles (managed from the profile switcher popover) ─────────────

    @property
    def current_user_profile(self) -> Optional[str]:
        """Name of the user profile currently on the scratch slot, if any —
        used by the switcher to label the active profile. Reads the shared
        state file, which every switch (this GUI's and the background
        daemon's) writes via activate_target, so it stays correct whoever
        performed the switch."""
        name = ap.active_user_profile()
        # Guard against a stale name that was since deleted.
        return name if name in ap.load_store() else None

    def user_profile_names(self) -> List[str]:
        return sorted(ap.load_store())

    def load_user_profile(self, name: str) -> bool:
        """Write a saved profile onto the mouse and activate it, so the user
        can use it or tweak it with Cheddar's regular tabs."""
        try:
            ap.activate_target(self._device, ap.SW_PREFIX + name, self._config)
        except Exception as exc:
            self._update_status_label(error=str(exc))
            return False
        self._editing_name = name
        return True

    def save_active_as_user_profile(self, name: str) -> None:
        """Re-capture the mouse's current setup and store it under `name`.
        Used when the user edits a loaded profile and hits Apply."""
        store = ap.load_store()
        store[name] = ap.capture_profile(self._device.active_profile)
        ap.save_store(store)

    def save_current_setup_dialog(self, parent: Gtk.Widget) -> Optional[str]:
        """Prompt for a name and save the mouse's current setup under it.
        Returns the saved name, or None if cancelled."""
        dlg = Gtk.Dialog(
            title=_("New Profile"),
            transient_for=parent,
            modal=True,
            use_header_bar=True,
        )
        dlg.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        ok = dlg.add_button(_("_Save"), Gtk.ResponseType.OK)
        ok.get_style_context().add_class("suggested-action")
        dlg.set_default_response(Gtk.ResponseType.OK)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=18)
        active = self._device.active_profile
        box.add(
            Gtk.Label(
                label=_(
                    "Saves how the mouse is set up right now — every "
                    "button, LED and resolution — as a profile you can "
                    "assign to a game."
                ),
                xalign=0,
                wrap=True,
                max_width_chars=44,
            )
        )
        entry = Gtk.Entry(
            placeholder_text=_("Name, e.g. Overwatch setup"),
            activates_default=True,
            text=self._editing_name or "",
        )
        box.add(entry)
        dlg.get_content_area().add(box)
        box.show_all()
        saved = None
        if dlg.run() == Gtk.ResponseType.OK and entry.get_text().strip():
            saved = entry.get_text().strip()
            store = ap.load_store()
            store[saved] = ap.capture_profile(active)
            ap.save_store(store)
            self._editing_name = None
        dlg.destroy()
        return saved

    def delete_user_profile(self, name: str) -> None:
        """Remove a saved profile and any rules that point at it."""
        store = ap.load_store()
        store.pop(name, None)
        ap.save_store(store)
        rules = self._config.get("rules", {})
        target = ap.SW_PREFIX + name
        for exe in [e for e, t in rules.items() if t == target]:
            rules.pop(exe)
        cfg_save(self._config)
        self._sync_watcher_rules()
        self._refresh_rules()

    def _target_label(self, target: RuleTarget) -> str:
        """Display name for a rule target: onboard profile name, or the
        software profile's name."""
        if ap.is_software_target(target):
            return ap.target_label(target)
        for p in self._device.profiles:
            if p.index == target:
                return _profile_label(p)
        return f"Profile {target}"

    def _on_watcher_switch(self, target: RuleTarget, exe_name: str) -> None:
        """Called from the watcher thread — must schedule GTK work via idle_add."""
        GLib.idle_add(self._switch_profile_main_thread, target, exe_name)

    def _switch_profile_main_thread(self, target: RuleTarget, exe_name: str) -> bool:
        try:
            ap.activate_target(self._device, target, self._config)
            self._update_status_label(last_switch=(exe_name, target))
            if self._config.get("notifications_enabled", True) and Notify:
                try:
                    p_name = self._target_label(target)
                    n = Notify.Notification.new(
                        "Cheddar AutoPilot",
                        _("Perfil activado: {}").format(p_name),
                        "io.github.rilorca.Cheddar",
                    )
                    try:
                        theme = Gtk.IconTheme.get_default()
                        pb = theme.load_icon("io.github.rilorca.Cheddar", 48, 0)
                        if pb:
                            n.set_image_from_pixbuf(pb)
                    except Exception:
                        pass
                    n.show()
                except Exception:
                    pass
        except Exception as exc:
            self._update_status_label(error=str(exc))
        return False  # GLib.idle_add one-shot

    def _update_status_label(
        self,
        last_switch=None,
        error: Optional[str] = None,
    ) -> None:
        running = self._watcher is not None and self._watcher.is_running()
        is_active = running or (hasattr(self, "_toggle") and self._toggle.get_active())
        if error:
            markup = (
                '<span foreground="#e01b24" weight="bold">⚠ Error</span> '
                + '<span size="small" foreground="#e01b24">'
                + GLib.markup_escape_text(error)
                + "</span>"
            )
        elif is_active:
            if last_switch:
                _exe, idx = last_switch
                p_name = self._target_label(idx)
            else:
                p_name = self.current_user_profile or _profile_label(self._device.active_profile)
            markup = (
                '<span background="#2ec27e33" foreground="#2ec27e" weight="bold">  Activo  </span>  '
                + '<span size="small" foreground="#ffffffaa">'
                + _("Último cambio:")
                + " "
                + f'<span weight="bold" foreground="#ffffff">{GLib.markup_escape_text(p_name)}</span>'
                + "</span>"
            )
        else:
            markup = (
                '<span background="#ffffff18" foreground="#ffffff88" weight="bold">  Inactivo  </span>  '
                + '<span size="small" foreground="#ffffff88">'
                + _("Automatización desactivada")
                + "</span>"
            )
        self._status_label.set_markup(markup)
        if hasattr(self, "_status_indicator"):
            self._status_indicator.queue_draw()

    def _on_draw_status_indicator(self, _widget, cr: cairo.Context) -> bool:
        active = self._toggle.get_active() if hasattr(self, "_toggle") else False
        if active:
            # Green pulse ring and dot
            cr.set_source_rgba(46 / 255.0, 194 / 255.0, 126 / 255.0, 0.45)
            cr.set_line_width(2.0)
            cr.arc(14, 14, 10.5, 0, 2 * math.pi)
            cr.stroke()

            cr.set_source_rgba(46 / 255.0, 194 / 255.0, 126 / 255.0, 1.0)
            cr.arc(14, 14, 5.0, 0, 2 * math.pi)
            cr.fill()
        else:
            # Dim grey ring and dot
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.25)
            cr.set_line_width(2.0)
            cr.arc(14, 14, 10.5, 0, 2 * math.pi)
            cr.stroke()

            cr.set_source_rgba(0.5, 0.5, 0.5, 0.6)
            cr.arc(14, 14, 5.0, 0, 2 * math.pi)
            cr.fill()
        return False

    def _on_notifications_toggled(self, switch: Gtk.Switch, _pspec) -> None:
        self._config["notifications_enabled"] = switch.get_active()
        cfg_save(self._config)

    # ── Signal handlers ────────────────────────────────────────────────────────

    def _on_toggle_changed(self, switch: Gtk.Switch, _param) -> None:
        active = switch.get_active()
        self._config["enabled"] = active
        cfg_save(self._config)
        if active:
            self._start_watcher()
        else:
            self._stop_watcher()

        # Update system tray menu if running inside Application
        app = Gio.Application.get_default()
        if app is not None and hasattr(app, "_tray") and app._tray:
            app._tray.update_menu()

    def _on_default_changed(self, combo: Gtk.ComboBoxText) -> None:
        aid = combo.get_active_id()
        if aid is not None:
            self._config["default_profile"] = int(aid)
            cfg_save(self._config)
            if self._watcher:
                self._watcher.update_rules(
                    self._config.get("rules", {}),
                    self._config["default_profile"],
                )

    def _on_add_rule(self, _btn: Gtk.Button) -> None:
        dlg = _RuleDialog(
            self.get_toplevel(),
            self._device.profiles,
            title=_("Add Rule"),
            default_profile=self._config.get("default_profile", 0),
        )
        resp = dlg.run()
        if resp == Gtk.ResponseType.OK and dlg.exe:
            self._config.setdefault("rules", {})[dlg.exe] = dlg.target
            cfg_save(self._config)
            self._sync_watcher_rules()
            self._refresh_rules()
        dlg.destroy()

    def _on_edit_rule(self, _btn: Gtk.Button, exe: str, profile_idx: int) -> None:
        dlg = _RuleDialog(
            self.get_toplevel(),
            self._device.profiles,
            exe=exe,
            profile_index=profile_idx,
            title=_("Edit Rule"),
            default_profile=self._config.get("default_profile", 0),
        )
        resp = dlg.run()
        if resp == Gtk.ResponseType.OK:
            rules = self._config.setdefault("rules", {})
            if dlg.exe and dlg.exe != exe:
                rules.pop(exe, None)
            if dlg.exe:
                rules[dlg.exe] = dlg.target
            cfg_save(self._config)
            self._sync_watcher_rules()
            self._refresh_rules()
        dlg.destroy()

    def _on_delete_rule(self, _btn: Gtk.Button, exe: str) -> None:
        confirm = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_('Delete rule for "{}"?').format(exe),
        )
        if confirm.run() == Gtk.ResponseType.YES:
            self._config.get("rules", {}).pop(exe, None)
            cfg_save(self._config)
            self._sync_watcher_rules()
            self._refresh_rules()
        confirm.destroy()

    def _sync_watcher_rules(self) -> None:
        if self._watcher:
            self._watcher.update_rules(
                self._config.get("rules", {}),
                self._config.get("default_profile", 0),
            )
        app = Gio.Application.get_default()
        if app is not None and hasattr(app, "notify_config_changed"):
            app.notify_config_changed()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Call when the window is closing to clean up the watcher thread.

        Deliberately does not go through _stop_watcher(): that updates the
        status label, and by the time we get here the widget tree is already
        being torn down. Requesting the stop is enough — the watcher is a
        daemon thread, so it will not keep the process alive.
        """
        if self._watcher is not None:
            self._watcher.request_stop()
            self._watcher = None
