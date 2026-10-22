# SPDX-License-Identifier: GPL-2.0-or-later

from gettext import gettext as _
import sys
from typing import Optional

import gi

from cheddar.ratbagd import RatbagdProfile

from .util.gobject import connect_signal_with_weak_ref

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # noqa


@Gtk.Template(resource_path="/io/github/rilorca/Cheddar/ui/ProfileRow.ui")
class ProfileRow(Gtk.ListBoxRow):
    """A Gtk.ListBoxRow subclass containing the widgets to display a profile in
    the profile poper."""

    __gtype_name__ = "ProfileRow"

    title: Gtk.Label = Gtk.Template.Child()  # type: ignore

    def __init__(self, profile: RatbagdProfile, *args, **kwargs) -> None:
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self._profile = profile
        connect_signal_with_weak_ref(
            self, self._profile, "notify::disabled", self._on_profile_notify_disabled
        )

        name = profile.name
        if not name:
            name = f"Profile {profile.index}"

        self.title.set_text(name)

        # Add pencil button for renaming
        box = self.get_child()
        if isinstance(box, Gtk.Box):
            edit_btn = Gtk.Button(relief=Gtk.ReliefStyle.NONE)
            edit_btn.add(
                Gtk.Image.new_from_icon_name("document-edit-symbolic", Gtk.IconSize.MENU)
            )
            edit_btn.set_tooltip_text(_("Rename this profile"))
            edit_btn.connect("clicked", self._on_rename_button_clicked)
            box.pack_end(edit_btn, False, False, 0)
            box.reorder_child(edit_btn, 1)

        self.show_all()
        self.set_visible(not profile.disabled)

    def _on_rename_button_clicked(self, _button: Gtk.Button) -> None:
        dlg = Gtk.Dialog(
            title=_("Rename Profile"),
            transient_for=self.get_toplevel(),
            modal=True,
            use_header_bar=True,
        )
        dlg.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        ok = dlg.add_button(_("_Save"), Gtk.ResponseType.OK)
        ok.get_style_context().add_class("suggested-action")
        dlg.set_default_response(Gtk.ResponseType.OK)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=18)
        current = self.title.get_text()
        box.add(Gtk.Label(label=_("Enter a new name for this profile:"), xalign=0))
        entry = Gtk.Entry(text=current, activates_default=True)
        box.add(entry)
        dlg.get_content_area().add(box)
        box.show_all()
        if dlg.run() == Gtk.ResponseType.OK:
            new_name = entry.get_text().strip()
            if new_name:
                try:
                    self._profile.name = new_name
                except Exception:
                    pass
                self.title.set_text(new_name)
        dlg.destroy()

    def _on_profile_notify_disabled(
        self, profile: RatbagdProfile, pspec: Optional[GObject.ParamSpec]
    ) -> None:
        self.set_visible(not profile.disabled)

    @Gtk.Template.Callback("_on_delete_button_clicked")
    def _on_delete_button_clicked(self, button: Gtk.Button) -> None:
        if not self._profile.is_active:
            self._profile.disabled = True
        else:
            # TODO: display this in the app
            print("Trying to disable the active profile", file=sys.stderr)

    def set_active(self) -> None:
        """Activates the profile paired with this row."""
        self._profile.set_active()

    @GObject.Property
    def name(self) -> str:
        return self.title.get_text()

    @GObject.Property
    def profile(self) -> RatbagdProfile:
        return self._profile
