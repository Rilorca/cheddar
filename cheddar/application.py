# SPDX-License-Identifier: GPL-2.0-or-later

import logging
from typing import Optional

from . import autopilot_config as cfg
from . import autopilot_profiles as ap
from .autopilot_watcher import AutoPilotWatcher, RuleTarget
from .ratbagd import Ratbagd
from .tray import TrayIcon
from .window import Window

import gi

gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa

logger = logging.getLogger("cheddar.application")


class Application(Gtk.Application):
    """A Gtk.Application subclass handling lifecycle, background AutoPilot
    watcher, system tray icon, and window management."""

    def __init__(self, ratbagd_api_version: int) -> None:
        """Instantiates a new Application."""
        Gtk.Application.__init__(
            self,
            application_id="io.github.rilorca.Cheddar",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        GLib.set_application_name("Cheddar")
        self.add_main_option(
            "background",
            ord("b"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Start minimized to system tray in background",
            None,
        )
        self._required_ratbagd_version = ratbagd_api_version
        self._window: Optional[Window] = None
        self._tray: Optional[TrayIcon] = None
        self._ratbagd: Optional[Ratbagd] = None
        self._watcher: Optional[AutoPilotWatcher] = None
        self._config = cfg.load()
        self._held: bool = False

    def do_startup(self) -> None:
        """Called once when application first starts."""
        Gtk.Application.do_startup(self)
        self._build_app_menu()

        # Keep application running in background when window is closed
        self.hold()
        self._held = True

        # Initialize background AutoPilot watcher
        self._sync_watcher()

        # Initialize system tray icon
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
            self._ratbagd.connect("daemon-disappeared", self._on_ratbagd_disappeared)
        return self._ratbagd

    def _on_ratbagd_disappeared(self, *args) -> None:
        logger.info("ratbagd daemon went idle or stopped; resetting connection")
        self._ratbagd = None

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        """Called on primary instance for every invocation."""
        options = command_line.get_options_dict()
        start_in_background = options.contains("background")

        if not start_in_background:
            self._show_window()

        return 0

    def do_activate(self) -> None:
        """Called on launch or when user activates application from launcher."""
        self._show_window()

    def _show_window(self) -> None:
        if self._window is not None:
            self._window.present()
            return
        self._window = Window(self.init_ratbagd, application=self)
        self._window.present()

    # ── AutoPilot background watcher ──────────────────────────────────────────

    def _effective_rules(self) -> dict:
        if not self._config.get("enabled", False):
            return {}
        return self._config.get("rules", {})

    def _sync_watcher(self) -> None:
        self._config = cfg.load()
        rules = self._effective_rules()
        default_profile = self._config.get("default_profile", 0)

        if self._watcher is None:
            self._watcher = AutoPilotWatcher(
                rules=rules,
                on_switch=self._on_watcher_switch,
                default_profile=default_profile,
            )
            self._watcher.start()
        else:
            self._watcher.update_rules(rules, default_profile)

    def _on_watcher_switch(self, target: RuleTarget, exe_name: str) -> None:
        GLib.idle_add(self._switch_main_thread, target, exe_name)

    def _switch_main_thread(self, target: RuleTarget, exe_name: str) -> bool:
        try:
            ratbag = self.init_ratbagd()
        except Exception as exc:
            logger.debug("ratbagd unavailable for switch: %s", exc)
            self._ratbagd = None
            return False

        try:
            devices = list(ratbag.devices)
        except Exception as exc:
            logger.debug("Failed to list ratbag devices: %s", exc)
            self._ratbagd = None
            return False

        for device in devices:
            try:
                ap.activate_target(device, target, self._config)
                logger.info("%s: '%s' -> %s", device.name, exe_name, target)
            except Exception as exc:
                logger.error("switch failed on %s: %s", device.name, exc)
                self._ratbagd = None
        return False

    def _is_autopilot_enabled(self) -> bool:
        return bool(self._config.get("enabled", False))

    def _get_status_text(self) -> str:
        return "AutoPilot: Active" if self._is_autopilot_enabled() else "AutoPilot: Inactive"

    def _toggle_autopilot(self) -> None:
        new_state = not self._is_autopilot_enabled()
        self._config["enabled"] = new_state
        cfg.save(self._config)
        self._sync_watcher()

        # Update running window GUI if open
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

    def notify_config_changed(self) -> None:
        """Called by GUI when rules or default profile are modified."""
        self._sync_watcher()
        if self._tray is not None:
            self._tray.update_menu()

    # ── Menu & Quit Actions ───────────────────────────────────────────────────

    def _build_app_menu(self) -> None:
        actions = [("about", self._about), ("quit", self._quit)]
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def _about(self, action: Gio.SimpleAction, param: None) -> None:
        builder = Gtk.Builder().new_from_resource(
            "/io/github/rilorca/Cheddar/AboutDialog.ui"
        )
        about: Optional[Gtk.AboutDialog] = builder.get_object("about_dialog")  # type: ignore
        assert about is not None
        about.set_transient_for(self.get_active_window())
        about.connect("response", lambda about, param: about.destroy())
        about.show()

    def _quit(self, action: Gio.SimpleAction, param: None) -> None:
        self._full_quit()

    def _full_quit(self) -> None:
        """Completely exit the application."""
        if self._watcher is not None:
            self._watcher.request_stop()
            self._watcher = None

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
