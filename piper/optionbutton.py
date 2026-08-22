# SPDX-License-Identifier: GPL-2.0-or-later

from typing import Optional
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


@Gtk.Template(resource_path="/org/freedesktop/Piper/ui/OptionButton.ui")
class OptionButton(Gtk.Button):
    """A Gtk.Button subclass that displays a label, a separator and a cog."""

    __gtype_name__ = "OptionButton"

    label: Gtk.Label = Gtk.Template.Child()  # type: ignore

    def __init__(self, label: Optional[str] = None, *args, **kwargs) -> None:
        """Instantiates a new OptionButton.

        @param label The text to display.
        """
        Gtk.Button.__init__(self, *args, **kwargs)
        if label is not None:
            self.set_label(label)

    def set_label(self, label: str) -> None:
        """Set the text to display.

        @param label The new text to display, as str.
        """
        self.label.set_text(label)
