# SPDX-License-Identifier: GPL-2.0-or-later

from typing import Optional

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # noqa


@Gtk.Template(resource_path="/org/freedesktop/Piper/ui/ErrorPerspective.ui")
class ErrorPerspective(Gtk.Box):
    """A perspective to present an error condition in a user-friendly manner."""

    __gtype_name__ = "ErrorPerspective"

    label_error: Gtk.Label = Gtk.Template.Child()  # type: ignore
    label_detail: Gtk.Label = Gtk.Template.Child()  # type: ignore
    _titlebar: Gtk.HeaderBar = Gtk.Template.Child()  # type: ignore

    def __init__(self, message: Optional[str] = None, *args, **kwargs) -> None:
        """Instantiates a new ErrorPerspective.

        @param message The error message to display, as str.
        """
        Gtk.Box.__init__(self, *args, **kwargs)
        if message is not None:
            self.set_message(message)

    @GObject.Property
    def name(self) -> str:
        """The name of this perspective."""
        return "error_perspective"

    @GObject.Property
    def titlebar(self) -> Gtk.Widget:
        """The titlebar to this perspective."""
        return self._titlebar

    @GObject.Property
    def can_go_back(self) -> bool:
        """Whether this perspective wants a back button to be displayed in case
        there is more than one connected device."""
        return False

    @GObject.Property
    def can_shutdown(self) -> bool:
        """Whether this perspective can safely shutdown."""
        return True

    def set_message(self, message: str) -> None:
        """Sets the error message.

        @param message The error message to display, as str.
        """
        self.label_error.set_label(message)

    def set_detail(self, detail: str) -> None:
        """Sets the detail message.

        @param message The detail message to display, as str.
        """
        self.label_detail.set_label(detail)
