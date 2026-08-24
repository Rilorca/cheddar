# SPDX-License-Identifier: GPL-2.0-or-later

from typing import Optional

from . import autopilot_config as cfg
from .ratbagd import Ratbagd
from .tray import TrayIcon
from .window import Window

import gi

gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa


class Application(Gtk.Application):
    """A Gtk.Application subclass to handle the application's initialization and
    integration with the GNOME stack. It implements the do_startup and
    do_activate methods and is responsible for the application's menus, icons,
    tray indicator, and lifetime."""

    def __init__(self, ratbagd_api_version: int) -> None:
        """Instantiates a new Application."""
        Gtk.Application.__init__(
            self,
            application_id="io.github.rilorca.Cheddar",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        GLib.set_application_name("Cheddar")
        self._required_ratbagd_version = ratbagd_api_version
        self._window: Optional[Window] = None
        self._tray: Optional[TrayIcon] = None
        self._held: bool = False

    def do_startup(self) -> None:
        """This function is called when the application is first started. All
        initialization should be done here, to prevent doing duplicate work in
        case another window is opened."""
        Gtk.Application.do_startup(self)
        self._build_app_menu()
        self._ratbagd: Optional[Ratbagd] = None

        # Hold application lifetime so it does not terminate when window is hidden
        self.hold()
        self._held = True

        # Initialize system tray indicator
        self._tray = TrayIcon(
            on_activate_window=self._show_window,
            on_toggle_autopilot=self._toggle_autopilot,
            on_quit=self._full_quit,
            is_autopilot_enabled=self._is_autopilot_enabled,
            get_status_text=self._get_status_text,
        )

    def init_ratbagd(self) -> Ratbagd:
        if self._ratbagd is None:
            self._ratbagd = Ratbagd(self._required_ratbagd_version)
        return self._ratbagd

    def do_activate(self) -> None:
        """This function is called when the user requests a new window to be
        opened or application is launched."""
        self._show_window()

    def _show_window(self) -> None:
        if self._window is None:
            self._window = Window(self.init_ratbagd, application=self)
        self._window.show_all()
        self._window.present()

    def _is_autopilot_enabled(self) -> bool:
        config = cfg.load()
        return bool(config.get("enabled", False))

    def _get_status_text(self) -> str:
        enabled = self._is_autopilot_enabled()
        return "AutoPilot: Active" if enabled else "AutoPilot: Inactive"

    def _toggle_autopilot(self) -> None:
        config = cfg.load()
        new_state = not config.get("enabled", False)
        config["enabled"] = new_state
        cfg.save(config)

        # Update running window GUI if present
        if self._window is not None:
            try:
                mouse_perspective = self._window._get_child("mouse_perspective")
                if hasattr(mouse_perspective, "autopilot_page") and mouse_perspective.autopilot_page:
                    page = mouse_perspective.autopilot_page
                    if hasattr(page, "_toggle"):
                        page._toggle.set_active(new_state)
            except Exception:
                pass

        if self._tray is not None:
            self._tray.update_menu()

    def _build_app_menu(self) -> None:
        # Set up the app menu
        actions = [("about", self._about), ("quit", self._quit)]
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def _about(self, action: Gio.SimpleAction, param: None) -> None:
        # Set up the about dialog.
        builder = Gtk.Builder().new_from_resource(
            "/io/github/rilorca/Cheddar/AboutDialog.ui"
        )
        about: Optional[Gtk.AboutDialog] = builder.get_object("about_dialog")  # type: ignore
        assert about is not None
        about.set_transient_for(self.get_active_window())
        about.connect("response", lambda about, param: about.destroy())
        about.show()

    def _quit(self, action: Gio.SimpleAction, param: None) -> None:
        # Primary menu quit action
        self._full_quit()

    def _full_quit(self) -> None:
        """Completely exit the application and destroy all windows."""
        if self._tray is not None:
            self._tray.set_visible(False)
            self._tray = None

        windows = list(self.get_windows())
        for window in windows:
            window.destroy()

        if self._held:
            self.release()
            self._held = False

        self.quit()
