# SPDX-License-Identifier: GPL-2.0-or-later

from gettext import gettext as _
from typing import Optional

from .leddialog import LedDialog
from .mousemap import MouseMap
from .optionbutton import OptionButton
from .ratbagd import RatbagdDevice, RatbagdLed, RatbagdProfile
from .util.gobject import connect_signal_with_weak_ref

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject  # noqa


class LedsPage(Gtk.Box):
    """The third stack page, exposing the LED configuration."""

    __gtype_name__ = "LedsPage"

    def __init__(
        self, ratbagd_device: RatbagdDevice, profile: RatbagdProfile, *args, **kwargs
    ) -> None:
        """Instantiates a new LedsPage.

        @param ratbag_device The ratbag device to configure, as
                             ratbagd.RatbagdDevice
        """
        Gtk.Box.__init__(self, *args, **kwargs)
        self._device = ratbagd_device

        self._profile = profile

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self._mousemap = MouseMap("#Leds", self._device, spacing=20, border_width=20)
        self.pack_start(self._mousemap, True, True, 0)
        self._sizegroup = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        for led in profile.leds:
            mode = _(RatbagdLed.LED_DESCRIPTION[led.mode])
            button = OptionButton(mode)
            button.connect("clicked", self._on_button_clicked, led)

            connect_signal_with_weak_ref(
                self, led, "notify::mode", self._on_led_mode_changed, button
            )

            self._mousemap.add(button, f"#led{led.index}")
            self._sizegroup.add_widget(button)

        bottom_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, margin_top=6, margin_bottom=8
        )
        bottom_bar.set_halign(Gtk.Align.CENTER)
        reset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        reset_icon = Gtk.Image.new_from_icon_name("edit-undo-symbolic", Gtk.IconSize.BUTTON)
        reset_lbl = Gtk.Label(label=_("Reset to defaults"))
        reset_box.pack_start(reset_icon, False, False, 0)
        reset_box.pack_start(reset_lbl, False, False, 0)
        reset_btn = Gtk.Button()
        reset_btn.add(reset_box)
        reset_btn.get_style_context().add_class("flat")
        reset_btn.get_style_context().add_class("reset-action")
        reset_btn.set_tooltip_text(_("Reset LEDs to default mode"))
        reset_btn.connect("clicked", self._on_reset_clicked)
        bottom_bar.pack_start(reset_btn, False, False, 0)
        self.pack_end(bottom_bar, False, False, 0)

        self.show_all()

    def _on_reset_clicked(self, _btn: Gtk.Button) -> None:
        for led in self._profile.leds:
            if RatbagdLed.Mode.CYCLE in led.modes:
                led.mode = RatbagdLed.Mode.CYCLE
            elif RatbagdLed.Mode.STATIC in led.modes:
                led.mode = RatbagdLed.Mode.STATIC
                led.color = (0, 200, 255)
            led.brightness = 100

    def _on_led_mode_changed(
        self, led: RatbagdLed, pspec: Optional[GObject.ParamSpec], button: OptionButton
    ) -> None:
        mode = _(RatbagdLed.LED_DESCRIPTION[led.mode])
        button.set_label(mode)

    def _on_button_clicked(self, button: OptionButton, led: RatbagdLed) -> None:
        # Presents the LedDialog to configure the LED corresponding to the
        # clicked button.
        dialog = LedDialog(led, transient_for=self.get_toplevel())
        dialog.connect("response", self._on_dialog_response, led)
        dialog.present()

    def _on_dialog_response(
        self, dialog: LedDialog, response: Gtk.ResponseType, led: RatbagdLed
    ) -> None:
        # The user either pressed cancel or apply. If it's apply, apply the
        # changes before closing the dialog, otherwise just close the dialog.
        if response == Gtk.ResponseType.APPLY:
            led.mode = dialog.mode
            led.color = dialog.color
            led.brightness = dialog.brightness
            led.effect_duration = dialog.effect_duration
        dialog.destroy()
