# SPDX-License-Identifier: GPL-2.0-or-later

import logging
from typing import Callable, Optional

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

logger = logging.getLogger(__name__)

# Try to import AppIndicator (AyatanaAppIndicator3 or AppIndicator3)
_Indicator = None
_IndicatorCategory = None
_IndicatorStatus = None

for mod_name in ("AyatanaAppIndicator3", "AppIndicator3"):
    try:
        gi.require_version(mod_name, "0.1")
        mod = getattr(__import__("gi.repository", fromlist=[mod_name]), mod_name)
        _Indicator = mod.Indicator
        _IndicatorCategory = mod.IndicatorCategory
        _IndicatorStatus = mod.IndicatorStatus
        logger.debug("using tray provider: %s", mod_name)
        break
    except (ValueError, ImportError, AttributeError):
        continue


class TrayIcon:
    """System tray / status icon integration for Cheddar.

    Uses AyatanaAppIndicator3 / AppIndicator3 on modern desktops (GNOME with
    AppIndicator extension, KDE Plasma, XFCE, Cinnamon), with a fallback to
    Gtk.StatusIcon if available.
    """

    def __init__(
        self,
        on_activate_window: Callable[[], None],
        on_toggle_autopilot: Callable[[], None],
        on_quit: Callable[[], None],
        is_autopilot_enabled: Callable[[], bool],
        get_status_text: Callable[[], str],
    ) -> None:
        self._on_activate_window = on_activate_window
        self._on_toggle_autopilot = on_toggle_autopilot
        self._on_quit = on_quit
        self._is_autopilot_enabled = is_autopilot_enabled
        self._get_status_text = get_status_text

        self._indicator = None
        self._status_icon = None
        self._menu: Optional[Gtk.Menu] = None
        self._status_item: Optional[Gtk.MenuItem] = None
        self._autopilot_check_item: Optional[Gtk.CheckMenuItem] = None

        self._init_tray()

    def _init_tray(self) -> None:
        icon_name = "io.github.rilorca.Cheddar-symbolic"
        self._menu = self._build_menu()

        if _Indicator is not None:
            try:
                self._indicator = _Indicator.new(
                    "io.github.rilorca.Cheddar",
                    icon_name,
                    _IndicatorCategory.APPLICATION_STATUS,
                )
                self._indicator.set_status(_IndicatorStatus.ACTIVE)
                self._indicator.set_menu(self._menu)
                self._indicator.set_title("Cheddar")
                if hasattr(self._indicator, "set_secondary_activate_target") and hasattr(self, "_show_item"):
                    self._indicator.set_secondary_activate_target(self._show_item)
                return
            except Exception as e:
                logger.warning("Failed to initialize AppIndicator tray: %s", e)

        # Fallback to Gtk.StatusIcon (X11 / older desktops)
        if hasattr(Gtk, "StatusIcon"):
            try:
                self._status_icon = Gtk.StatusIcon.new_from_icon_name(icon_name)
                self._status_icon.set_title("Cheddar")
                self._status_icon.set_tooltip_text("Cheddar - AutoPilot")
                self._status_icon.connect("activate", lambda *_: self._on_activate_window())
                self._status_icon.connect("popup-menu", self._on_status_icon_popup)
                self._status_icon.set_visible(True)
            except Exception as e:
                logger.warning("Failed to initialize Gtk.StatusIcon: %s", e)

    def _on_status_icon_popup(self, icon, button, activate_time) -> None:
        self.update_menu()
        if self._menu:
            self._menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, activate_time)

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        # Status text header (e.g. "AutoPilot: Active")
        self._status_item = Gtk.MenuItem(label=self._get_status_text())
        self._status_item.set_sensitive(False)
        menu.append(self._status_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Open window
        self._show_item = Gtk.MenuItem(label="Show Cheddar")
        self._show_item.connect("activate", lambda *_: self._on_activate_window())
        menu.append(self._show_item)

        # Toggle AutoPilot
        self._autopilot_check_item = Gtk.CheckMenuItem(label="Enable AutoPilot")
        self._autopilot_check_item.set_active(self._is_autopilot_enabled())
        self._autopilot_check_item.connect("toggled", self._on_autopilot_toggled)
        menu.append(self._autopilot_check_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem(label="Quit Cheddar")
        quit_item.connect("activate", lambda *_: self._on_quit())
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _on_autopilot_toggled(self, item: Gtk.CheckMenuItem) -> None:
        current_state = self._is_autopilot_enabled()
        new_state = item.get_active()
        if current_state != new_state:
            self._on_toggle_autopilot()

    def update_menu(self) -> None:
        """Refresh the tray menu items to match current app state."""
        if self._status_item:
            self._status_item.set_label(self._get_status_text())
        if self._autopilot_check_item:
            # Block handler during programmatic update
            self._autopilot_check_item.handler_block_by_func(self._on_autopilot_toggled)
            self._autopilot_check_item.set_active(self._is_autopilot_enabled())
            self._autopilot_check_item.handler_unblock_by_func(self._on_autopilot_toggled)

    def set_visible(self, visible: bool) -> None:
        if self._indicator is not None and _IndicatorStatus is not None:
            status = _IndicatorStatus.ACTIVE if visible else _IndicatorStatus.PASSIVE
            self._indicator.set_status(status)
        elif self._status_icon is not None:
            self._status_icon.set_visible(visible)
