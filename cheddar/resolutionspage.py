# SPDX-License-Identifier: GPL-2.0-or-later

from gettext import gettext as _
from typing import Optional

from .mousemap import MouseMap
from .ratbagd import RatbagdButton, RatbagdDevice, RatbagdProfile
from .resolutionrow import ResolutionRow

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


@Gtk.Template(resource_path="/io/github/rilorca/Cheddar/ui/ResolutionsPage.ui")
class ResolutionsPage(Gtk.Box):
    """The first stack page, exposing the resolution configuration with its
    report rate buttons and resolutions list."""

    __gtype_name__ = "ResolutionsPage"

    _resolution_labels = [
        RatbagdButton.ActionSpecial.RESOLUTION_CYCLE_UP,
        RatbagdButton.ActionSpecial.RESOLUTION_CYCLE_DOWN,
        RatbagdButton.ActionSpecial.RESOLUTION_UP,
        RatbagdButton.ActionSpecial.RESOLUTION_DOWN,
        RatbagdButton.ActionSpecial.RESOLUTION_ALTERNATE,
        RatbagdButton.ActionSpecial.RESOLUTION_DEFAULT,
    ]

    add_resolution_row: Gtk.ListBoxRow = Gtk.Template.Child()  # type: ignore
    listbox: Gtk.ListBox = Gtk.Template.Child()  # type: ignore

    def __init__(
        self, ratbagd_device: RatbagdDevice, profile: RatbagdProfile, *args, **kwargs
    ) -> None:
        """Instantiates a new ResolutionsPage.

        @param ratbag_device The ratbag device to configure, as
                             ratbagd.RatbagdDevice
        """
        Gtk.Box.__init__(self, *args, **kwargs)

        self._device = ratbagd_device
        self._last_activated_row: Optional[ResolutionRow] = None
        self._profile = profile

        mousemap = MouseMap("#Buttons", self._device, spacing=20, border_width=20)
        self.pack_start(mousemap, True, True, 0)
        # Place the MouseMap on the left
        self.reorder_child(mousemap, 0)
        for button in profile.buttons:
            if (
                button.action_type == RatbagdButton.ActionType.SPECIAL
                and button.special in self._resolution_labels
            ):
                label = Gtk.Label(
                    label=_(RatbagdButton.SPECIAL_DESCRIPTION[button.special])
                )
                mousemap.add(label, f"#button{button.index}")
        mousemap.show_all()

        self.listbox.foreach(Gtk.Widget.destroy)
        for resolution in profile.resolutions:
            row = ResolutionRow(resolution, self)
            self.listbox.insert(row, resolution.index)

    btn_reset_resolutions: Gtk.Button = Gtk.Template.Child()  # type: ignore

    @Gtk.Template.Callback("on_row_activated")
    def on_row_activated(self, _listbox: Gtk.ListBox, row: ResolutionRow) -> None:
        if row is self._last_activated_row:
            self._last_activated_row = None
            row.toggle_revealer()
        else:
            if self._last_activated_row is not None:
                self._last_activated_row.toggle_revealer()

            if row is self.add_resolution_row:
                print("TODO: RatbagdProfile needs a way to add resolutions")
                self._last_activated_row = None
            else:
                self._last_activated_row = row
                row.toggle_revealer()

    @Gtk.Template.Callback("_on_reset_clicked")
    def _on_reset_clicked(self, _button: Gtk.Button) -> None:
        resolutions = self._profile.resolutions
        if not resolutions:
            return

        n = len(resolutions)
        if n == 1:
            dpis = [800]
        elif n == 2:
            dpis = [800, 1600]
        elif n == 3:
            dpis = [400, 800, 1600]
        elif n == 4:
            dpis = [400, 800, 1600, 3200]
        else:
            dpis = [400, 800, 1200, 1600, 3200][:n]

        for i, res in enumerate(resolutions):
            target_dpi = dpis[i] if i < len(dpis) else 800
            if res.resolutions and target_dpi not in res.resolutions:
                target_dpi = min(res.resolutions, key=lambda x: abs(x - target_dpi))

            cur = res.resolution
            if len(cur) == 1:
                res.resolution = (target_dpi,)
            else:
                res.resolution = (target_dpi, target_dpi)

        default_idx = 1 if len(resolutions) > 1 else 0
        resolutions[default_idx].set_default()

        # Refresh UI rows
        self._last_activated_row = None
        self.listbox.foreach(Gtk.Widget.destroy)
        for resolution in self._profile.resolutions:
            row = ResolutionRow(resolution, self)
            self.listbox.insert(row, resolution.index)
        self.listbox.show_all()
