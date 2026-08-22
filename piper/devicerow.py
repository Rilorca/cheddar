# SPDX-License-Identifier: GPL-2.0-or-later

from piper.svg import get_svg

import sys

import gi

from .ratbagd import RatbagdDevice

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, GObject, Gtk, Rsvg  # noqa


@Gtk.Template(resource_path="/org/freedesktop/Piper/ui/DeviceRow.ui")
class DeviceRow(Gtk.ListBoxRow):
    """A Gtk.ListBoxRow subclass to present devices in the welcome
    perspective."""

    __gtype_name__ = "DeviceRow"

    image: Gtk.Image = Gtk.Template.Child()  # type: ignore
    title: Gtk.Label = Gtk.Template.Child()  # type: ignore

    def __init__(self, device: RatbagdDevice, *args, **kwargs) -> None:
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self._device = device

        fw_version = device.firmware_version
        if fw_version:
            self.title.set_markup(
                f"{device.name} <span foreground='gray'>(firmware {fw_version})</span>"
            )
        else:
            self.title.set_text(device.name)

        try:
            svg_bytes = get_svg(device.model)
            assert svg_bytes is not None
            handle = Rsvg.Handle.new_from_data(svg_bytes)
            assert handle is not None
            svg = handle.get_pixbuf_sub("#Device")
            handle.close()
            if svg is None:
                print(
                    f"Device {device.name}'s SVG is incompatible",
                    file=sys.stderr,
                )
            else:
                svg = svg.scale_simple(50, 50, GdkPixbuf.InterpType.BILINEAR)
                if svg is None:
                    print("Cannot resize device SVG", file=sys.stderr)
                else:
                    self.image.set_from_pixbuf(svg)
        except FileNotFoundError:
            print(
                f"Device {device.name} has no image or its path is invalid",
                file=sys.stderr,
            )

        self.show_all()

    @GObject.Property
    def device(self) -> RatbagdDevice:
        return self._device
