# SPDX-License-Identifier: GPL-2.0-or-later
#
# autopilotpage.py — part of Piper AutoPilot fork
#
# Adds an "AutoPilot" tab to Piper's per-device stack switcher.
# The page lets users:
#   • Map game executables to profiles (Add / Edit / Delete rules)
#   • Choose a default profile (used when no mapped game is running)
#   • Start / stop the background process watcher
#
# Design: pure-Python GTK3 widget — no extra .ui file required.
# Follows the same style conventions as Piper's other pages.

import threading
from gettext import gettext as _
from typing import Dict, List, Optional

from .autopilot_config import load as cfg_load, save as cfg_save
from .autopilot_games import installed_games
from .autopilot_watcher import AutoPilotWatcher
from .ratbagd import RatbagdDevice, RatbagdProfile

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, GLib, Gtk  # noqa


def _load_game_icon(path: Optional[str]) -> Optional[GdkPixbuf.Pixbuf]:
    """Load a game icon scaled for the picker; themed fallback when absent."""
    if path:
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_size(path, 20, 20)
        except GLib.Error:
            pass
    try:
        return Gtk.IconTheme.get_default().load_icon(
            "applications-games-symbolic", 16, 0
        )
    except GLib.Error:
        return None


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
        if (
            self._default_profile is not None
            and self.profile_index == self._default_profile
        ):
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
    def profile_index(self) -> int:
        aid = self._profile_combo.get_active_id()
        return int(aid) if aid is not None else 0


# ─── Main page widget ──────────────────────────────────────────────────────────


class AutoPilotPage(Gtk.Box):
    """
    The AutoPilot tab shown inside Piper's per-device stack-switcher.

    Integrates with MousePerspective exactly like ResolutionsPage or
    AdvancedPage: constructed with (device, profile) and added to the
    GtkStack via stack.add_titled().

    One instance is shared across profile switches (unlike other pages)
    because the watcher is device-wide, not per-profile.
    """

    def __init__(self, device: RatbagdDevice) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0,
        )
        self._device = device
        self._config: Dict = cfg_load()
        self._watcher: Optional[AutoPilotWatcher] = None

        self._build_ui()

        # Auto-restart watcher if it was enabled last session
        if self._config.get("enabled", False):
            GLib.idle_add(self._start_watcher)

        self.show_all()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Left column: controls
        left = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            border_width=20,
            width_request=320,
        )
        self.pack_start(left, False, False, 0)

        # ── Section: Status ───────────────────────────────────────────────────
        status_lbl = Gtk.Label(xalign=0)
        status_lbl.set_markup(f'<span weight="bold">{_("Auto-switch profiles")}</span>')
        left.pack_start(status_lbl, False, False, 0)

        desc = Gtk.Label(
            xalign=0,
            wrap=True,
            max_width_chars=36,
            margin_top=4,
            margin_bottom=16,
        )
        desc.set_markup(
            '<span size="small" foreground="grey">'
            + GLib.markup_escape_text(
                _(
                    "AutoPilot watches running processes and switches your "
                    "{} profile automatically when a mapped game is detected."
                ).format(self._device.name)
            )
            + "</span>"
        )
        left.pack_start(desc, False, False, 0)

        # Start/stop toggle
        toggle_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toggle_lbl = Gtk.Label(label=_("Enable AutoPilot"), xalign=0, hexpand=True)
        self._toggle = Gtk.Switch(valign=Gtk.Align.CENTER)
        self._toggle.set_active(self._config.get("enabled", False))
        self._toggle.connect("notify::active", self._on_toggle_changed)
        toggle_row.pack_start(toggle_lbl, True, True, 0)
        toggle_row.pack_start(self._toggle, False, False, 0)
        left.pack_start(toggle_row, False, False, 0)

        # Status indicator
        self._status_label = Gtk.Label(
            xalign=0,
            margin_top=6,
            margin_bottom=18,
        )
        self._update_status_label()
        left.pack_start(self._status_label, False, False, 0)

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_bottom=16)
        left.pack_start(sep1, False, False, 0)

        # ── Section: Default profile ──────────────────────────────────────────
        def_lbl = Gtk.Label(xalign=0, margin_bottom=6)
        def_lbl.set_markup(
            '<span size="small" weight="bold">'
            + _("DEFAULT PROFILE").upper()
            + "</span>"
        )
        left.pack_start(def_lbl, False, False, 0)

        def_sub = Gtk.Label(xalign=0, wrap=True, max_width_chars=36, margin_bottom=8)
        def_sub.set_markup(
            '<span size="small" foreground="grey">'
            + _("Profile to use when no mapped game is running.")
            + "</span>"
        )
        left.pack_start(def_sub, False, False, 0)

        self._default_combo = Gtk.ComboBoxText()
        for p in self._device.profiles:
            self._default_combo.append(str(p.index), _profile_label(p))
        self._default_combo.set_active_id(str(self._config.get("default_profile", 0)))
        if self._default_combo.get_active_id() is None:
            self._default_combo.set_active(0)
        self._default_combo.connect("changed", self._on_default_changed)
        left.pack_start(self._default_combo, False, False, 0)

        # ─── Right column: rules list ─────────────────────────────────────────
        right = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            border_width=20,
            hexpand=True,
        )
        self.pack_start(right, True, True, 0)

        # Header
        rules_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_bottom=8,
        )
        rules_title = Gtk.Label(hexpand=True)
        rules_title.set_markup(f'<span weight="bold">{_("Game rules")}</span>')
        rules_title.set_xalign(0)
        self._add_btn = Gtk.Button(label=_("+ Add rule"))
        self._add_btn.get_style_context().add_class("suggested-action")
        self._add_btn.connect("clicked", self._on_add_rule)
        rules_header.pack_start(rules_title, True, True, 0)
        rules_header.pack_start(self._add_btn, False, False, 0)
        right.pack_start(rules_header, False, False, 0)

        sub2 = Gtk.Label(xalign=0, margin_bottom=14)
        sub2.set_markup(
            '<span size="small" foreground="grey">'
            + _(
                "Each rule maps a game's executable name to a profile. "
                "AutoPilot checks every 2 seconds."
            )
            + "</span>"
        )
        right.pack_start(sub2, False, False, 0)

        # Scrollable rules list
        scroll = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            hexpand=True,
            vexpand=True,
        )
        self._rules_box = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
        )
        self._rules_box.set_header_func(self._rules_header_func)
        scroll.add(self._rules_box)
        right.pack_start(scroll, True, True, 0)

        self._refresh_rules()

    def _rules_header_func(self, row, before):
        """Add a separator between rows (Piper style)."""
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
            spacing=8,
            border_width=8,
        )

        # Game icon
        icon = Gtk.Image.new_from_icon_name(
            "applications-games-symbolic", Gtk.IconSize.MENU
        )
        box.pack_start(icon, False, False, 0)

        # Executable name
        exe_lbl = Gtk.Label(label=exe, xalign=0, hexpand=True)
        exe_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        box.pack_start(exe_lbl, True, True, 0)

        # Arrow
        arrow = Gtk.Label(label="→")
        arrow.get_style_context().add_class("dim-label")
        box.pack_start(arrow, False, False, 0)

        # Profile name
        p_label = f"Profile {profile_idx}"
        for p in self._device.profiles:
            if p.index == profile_idx:
                p_label = _profile_label(p)
                break
        profile_lbl = Gtk.Label(label=p_label, xalign=1)
        profile_lbl.get_style_context().add_class("dim-label")
        box.pack_start(profile_lbl, False, False, 4)

        # Edit button
        edit_btn = Gtk.Button(relief=Gtk.ReliefStyle.NONE)
        edit_btn.add(
            Gtk.Image.new_from_icon_name("document-edit-symbolic", Gtk.IconSize.MENU)
        )
        edit_btn.set_tooltip_text(_("Edit this rule"))
        edit_btn.connect("clicked", self._on_edit_rule, exe, profile_idx)
        box.pack_start(edit_btn, False, False, 0)

        # Delete button
        del_btn = Gtk.Button(relief=Gtk.ReliefStyle.NONE)
        del_btn.add(
            Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.MENU)
        )
        del_btn.set_tooltip_text(_("Delete this rule"))
        del_btn.get_style_context().add_class("destructive-action")
        del_btn.connect("clicked", self._on_delete_rule, exe)
        box.pack_start(del_btn, False, False, 0)

        row.add(box)
        return row

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

    def _on_watcher_switch(self, profile_index: int, exe_name: str) -> None:
        """Called from the watcher thread — must schedule GTK work via idle_add."""
        GLib.idle_add(self._switch_profile_main_thread, profile_index, exe_name)

    def _switch_profile_main_thread(self, profile_index: int, exe_name: str) -> bool:
        for profile in self._device.profiles:
            if profile.index == profile_index:
                try:
                    profile.set_active()
                    self._device.commit()
                    self._update_status_label(last_switch=(exe_name, profile_index))
                except Exception as exc:
                    self._update_status_label(error=str(exc))
                break
        return False  # GLib.idle_add one-shot

    def _update_status_label(
        self,
        last_switch=None,
        error: Optional[str] = None,
    ) -> None:
        running = self._watcher is not None and self._watcher.is_running()
        if error:
            markup = (
                '<span foreground="red">⚠ '
                + GLib.markup_escape_text(_("Error: {}").format(error))
                + "</span>"
            )
        elif last_switch:
            exe, idx = last_switch
            p_name = f"Profile {idx}"
            for p in self._device.profiles:
                if p.index == idx:
                    p_name = _profile_label(p)
                    break
            markup = (
                '<span foreground="green">● </span>'
                + '<span size="small">'
                + GLib.markup_escape_text(
                    _("Active — last switch: {} → {}").format(exe, p_name)
                )
                + "</span>"
            )
        elif running:
            markup = (
                '<span foreground="green">● </span>'
                + '<span size="small" foreground="grey">'
                + _("Watching for games…")
                + "</span>"
            )
        else:
            markup = (
                '<span foreground="grey">○ </span>'
                + '<span size="small" foreground="grey">'
                + _("Inactive")
                + "</span>"
            )
        self._status_label.set_markup(markup)

    # ── Signal handlers ────────────────────────────────────────────────────────

    def _on_toggle_changed(self, switch: Gtk.Switch, _param) -> None:
        active = switch.get_active()
        self._config["enabled"] = active
        cfg_save(self._config)
        if active:
            self._start_watcher()
        else:
            self._stop_watcher()

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
            self._config.setdefault("rules", {})[dlg.exe] = dlg.profile_index
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
                rules[dlg.exe] = dlg.profile_index
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
