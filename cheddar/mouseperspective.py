# SPDX-License-Identifier: GPL-2.0-or-later

from gettext import gettext as _
from typing import Optional

from . import autopilot_profiles as ap
from .autopilotpage import AutoPilotPage
from .buttonspage import ButtonsPage
from .profilerow import ProfileRow
from .ratbagd import RatbagdDevice, RatbagdProfile
from .resolutionspage import ResolutionsPage
from .advancedpage import AdvancedPage
from .ledspage import LedsPage
from .util.gobject import connect_signal_with_weak_ref

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, GObject, Gtk  # noqa


class UserProfileRow(Gtk.ListBoxRow):
    """A row in the profile switcher for a user-created (AutoPilot) profile.

    Marked with a person icon to distinguish it from the mouse's onboard
    profiles. Activating it writes the profile onto the mouse.
    """

    def __init__(self, name: str, on_delete) -> None:
        super().__init__()
        self.sw_name = name
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, border_width=4)
        mark = Gtk.Image.new_from_icon_name(
            "avatar-default-symbolic", Gtk.IconSize.MENU
        )
        mark.set_tooltip_text(_("Your profile — stored on this PC"))
        box.pack_start(mark, False, False, 4)
        lbl = Gtk.Label(label=name, xalign=0, hexpand=True)
        lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        box.pack_start(lbl, True, True, 0)
        del_btn = Gtk.Button(relief=Gtk.ReliefStyle.NONE)
        del_btn.add(
            Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.MENU)
        )
        del_btn.set_tooltip_text(_("Delete this profile"))
        del_btn.connect("clicked", lambda _b: on_delete(name))
        box.pack_start(del_btn, False, False, 0)
        self.add(box)
        self.show_all()

    @GObject.Property
    def name(self) -> str:
        return self.sw_name


@Gtk.Template(resource_path="/io/github/rilorca/Cheddar/ui/MousePerspective.ui")
class MousePerspective(Gtk.Overlay):
    """The perspective to configure a mouse."""

    __gtype_name__ = "MousePerspective"

    _titlebar: Gtk.HeaderBar = Gtk.Template.Child()  # type: ignore
    add_profile_button: Gtk.Button = Gtk.Template.Child()  # type: ignore
    button_commit: Gtk.Button = Gtk.Template.Child()  # type: ignore
    button_profile: Gtk.Button = Gtk.Template.Child()  # type: ignore
    label_profile: Gtk.Label = Gtk.Template.Child()  # type: ignore
    listbox_profiles: Gtk.ListBox = Gtk.Template.Child()  # type: ignore
    notification_error: Gtk.Revealer = Gtk.Template.Child()  # type: ignore
    stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore

    def __init__(self, *args, **kwargs) -> None:
        """Instantiates a new MousePerspective."""
        Gtk.Overlay.__init__(self, *args, **kwargs)
        self._device: Optional[RatbagdDevice] = None
        self._profile: Optional[RatbagdProfile] = None
        self._notification_error_timeout_id = 0
        self._autopilot_page: Optional[AutoPilotPage] = None

    @GObject.Property
    def name(self) -> str:
        """The name of this perspective."""
        return "mouse_perspective"

    @GObject.Property
    def titlebar(self) -> Gtk.Widget:
        """The titlebar to this perspective."""
        return self._titlebar

    @GObject.Property
    def can_go_back(self) -> bool:
        """Whether this perspective wants a back button to be displayed in case
        there is more than one connected device."""
        return True

    @GObject.Property
    def can_shutdown(self) -> bool:
        if self._device is None:
            return True

        """Whether this perspective can safely shutdown."""
        return all(not profile.dirty for profile in self._device.profiles)

    @GObject.Property
    def device(self) -> RatbagdDevice:
        assert self._device is not None
        return self._device

    def set_device(self, device: RatbagdDevice) -> None:
        self._device = device
        connect_signal_with_weak_ref(
            self, device, "resync", lambda _: self._show_notification_error()
        )
        connect_signal_with_weak_ref(
            self,
            self._device,
            "active-profile-changed",
            self._on_active_profile_changed,
        )

        # AutoPilot: create once per device (device-scoped, not profile-scoped).
        # This must happen before _set_profile(), which is what populates the
        # stack: it re-adds the AutoPilot page on every profile switch, so if
        # the page did not exist yet the tab would be missing until the user
        # switched profiles by hand.
        if self._autopilot_page is not None:
            self._autopilot_page.shutdown()
        self._autopilot_page = AutoPilotPage(device)

        active_profile = device.active_profile
        assert active_profile is not None
        self._set_profile(active_profile)

        self.button_profile.set_visible(len(device.profiles) > 1)

        self.listbox_profiles.foreach(Gtk.Widget.destroy)
        for profile in device.profiles:
            connect_signal_with_weak_ref(
                self, profile, "notify::disabled", self._on_profile_notify_disabled
            )
            connect_signal_with_weak_ref(
                self, profile, "notify::dirty", self._on_profile_notify_dirty
            )
            row = ProfileRow(profile)
            self.listbox_profiles.insert(row, profile.index)

        self._on_profile_notify_disabled(active_profile, None)

        self._select_profile_row(active_profile)

        # AutoPilot reserves one onboard slot for the user's named profiles;
        # hide it from the switcher while AutoPilot is on so nobody edits a
        # slot that gets overwritten on the next game launch.
        self._autopilot_page.connect_enabled_changed(self._update_reserved_slot_row)
        self._update_reserved_slot_row()

        # The user's own profiles list right below the onboard ones.
        self._refresh_user_profile_rows()

        # Two games mapped to different user profiles share the scratch slot,
        # so switching between them never fires active-profile-changed. Watch
        # the shared state file instead — every activate_target (ours or the
        # background daemon's) rewrites it — and refresh the label from it.
        self._state_monitor = Gio.File.new_for_path(ap._STATE_FILE).monitor_file(
            Gio.FileMonitorFlags.NONE, None
        )
        self._state_monitor.connect("changed", self._on_autopilot_state_changed)

    def _on_autopilot_state_changed(self, _monitor, _file, _other, event) -> None:
        if event not in (
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
        ):
            return
        # Defer briefly: this file event races the D-Bus active-profile
        # update, and refreshing with a stale active index would label the
        # wrong row. A short delay lets both settle.
        GLib.timeout_add(400, self._refresh_active_label)

    def _refresh_active_label(self) -> bool:
        if self._device is not None:
            active = self._device.active_profile
            if active is not None:
                self._select_profile_row(active)
        return False  # one-shot

    def _update_reserved_slot_row(self) -> None:
        page = self._autopilot_page
        if page is None:
            return
        hide = page.autopilot_enabled
        slot = page.scratch_slot
        for row in self.listbox_profiles.get_children():
            if isinstance(row, ProfileRow) and row.profile.index == slot:
                row.set_no_show_all(hide)
                row.set_visible(not hide)

    def _refresh_user_profile_rows(self) -> None:
        if self._autopilot_page is None:
            return
        for row in self.listbox_profiles.get_children():
            if isinstance(row, UserProfileRow):
                self.listbox_profiles.remove(row)
        for name in self._autopilot_page.user_profile_names():
            self.listbox_profiles.add(UserProfileRow(name, self._delete_user_profile))

    def _delete_user_profile(self, name: str) -> None:
        confirm = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_(
                'Delete profile "{}"? Game rules that use it will be removed too.'
            ).format(name),
        )
        if confirm.run() == Gtk.ResponseType.YES:
            assert self._autopilot_page is not None
            self._autopilot_page.delete_user_profile(name)
            self._refresh_user_profile_rows()
        confirm.destroy()

    def _select_profile_row(self, profile: RatbagdProfile) -> None:
        page = self._autopilot_page
        # When the active profile is the slot AutoPilot manages, what's on
        # the mouse is one of the user's named profiles — label and select
        # that instead of the hidden "Profile N" slot.
        if (
            page is not None
            and page.autopilot_enabled
            and profile.index == page.scratch_slot
            and page.current_user_profile
        ):
            self.label_profile.set_label(page.current_user_profile)
            for row in self.listbox_profiles.get_children():
                if (
                    isinstance(row, UserProfileRow)
                    and row.sw_name == page.current_user_profile
                ):
                    self.listbox_profiles.select_row(row)
                    break
            return
        for row in self.listbox_profiles.get_children():
            if isinstance(row, ProfileRow) and row.profile is profile:
                self.listbox_profiles.select_row(row)
                self.label_profile.set_label(row.name)
                break

    def _set_profile(self, profile: RatbagdProfile) -> None:
        assert self._device is not None

        self._select_profile_row(profile)

        self._profile = profile

        # Remember the visible tab so profile switches (including the ones
        # AutoPilot triggers in the background) don't yank the user back to
        # the first tab.
        visible_child_name = self.stack.get_visible_child_name()

        # The AutoPilot page is device-scoped and must survive profile
        # switches, so detach it before the foreach below: Gtk.Widget.destroy
        # recursively destroys a container's children even while Python holds
        # a reference, which would leave the tab as an empty shell when
        # re-added.
        if (
            self._autopilot_page is not None
            and self._autopilot_page.get_parent() is self.stack
        ):
            self.stack.remove(self._autopilot_page)

        self.stack.foreach(Gtk.Widget.destroy)
        if profile.resolutions:
            self.stack.add_titled(
                ResolutionsPage(self._device, profile), "resolutions", _("Resolutions")
            )
        if profile.buttons:
            self.stack.add_titled(
                ButtonsPage(self._device, profile), "buttons", _("Buttons")
            )
        if profile.leds:
            self.stack.add_titled(LedsPage(self._device, profile), "leds", _("LEDs"))
        # TODO: get rid of this duplicated logic.
        are_report_rates_supported = (
            profile.report_rate != 0 and len(profile.report_rates) != 0
        )
        if (
            profile.angle_snapping != -1
            or profile.debounces
            or are_report_rates_supported
        ):
            self.stack.add_titled(
                AdvancedPage(self._device, profile), "advanced", _("Advanced")
            )

        # AutoPilot tab: always present, device-scoped (re-attach after stack.foreach(destroy))
        if self._autopilot_page is not None:
            self.stack.add_titled(self._autopilot_page, "autopilot", _("AutoPilot"))

        # Restore the previously visible tab if it still exists.
        if (
            visible_child_name is not None
            and self.stack.get_child_by_name(visible_child_name) is not None
        ):
            self.stack.set_visible_child_name(visible_child_name)

        self._on_profile_notify_dirty(profile, None)

    def _hide_notification_error(self) -> None:
        if self._notification_error_timeout_id != 0:
            GLib.Source.remove(self._notification_error_timeout_id)
            self._notification_error_timeout_id = 0
        self.notification_error.set_reveal_child(False)

    def _show_notification_error(self) -> None:
        self.notification_error.set_reveal_child(True)
        self._notification_error_timeout_id = GLib.timeout_add_seconds(
            5, self._on_notification_error_timeout
        )

    def _on_active_profile_changed(
        self, _device: RatbagdDevice, profile: RatbagdProfile
    ) -> None:
        # TODO: preserve the active tab.
        self._set_profile(profile)

    def _on_notification_error_timeout(self) -> bool:
        self._hide_notification_error()
        return False

    @Gtk.Template.Callback("_on_save_button_clicked")
    def _on_save_button_clicked(self, _button: Gtk.Button) -> None:
        assert self._device is not None
        self._device.commit()
        # If the active profile is a user profile loaded on the scratch slot,
        # persist the edits back to its stored definition too — otherwise
        # "Apply" would only touch the mouse's scratch slot, which gets
        # overwritten on the next game launch, losing the changes.
        page = self._autopilot_page
        if page is None or not page.autopilot_enabled:
            return
        name = page.current_user_profile
        active = self._device.active_profile
        if (
            name is not None
            and active is not None
            and active.index == page.scratch_slot
        ):
            page.save_active_as_user_profile(name)

    @Gtk.Template.Callback("_on_notification_error_close_clicked")
    def _on_notification_error_close_clicked(self, button: Gtk.Button) -> None:
        self._hide_notification_error()

    @Gtk.Template.Callback("_on_profile_row_activated")
    def _on_profile_row_activated(
        self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow
    ) -> None:
        if isinstance(row, UserProfileRow):
            # A user profile: write it onto the mouse's reserved slot.
            assert self._autopilot_page is not None
            if self._autopilot_page.load_user_profile(row.sw_name):
                self.label_profile.set_label(row.sw_name)
                self.listbox_profiles.select_row(row)
        else:
            row.set_active()

    @Gtk.Template.Callback("_on_add_profile_button_clicked")
    def _on_add_profile_button_clicked(self, button: Gtk.Button) -> None:
        assert self._device is not None
        # Fork behavior: create a new user profile from the mouse's current
        # setup (the upstream behavior — enabling a disabled onboard slot —
        # doesn't apply to mice like the G600 whose slots are all enabled).
        if self._autopilot_page is not None:
            saved = self._autopilot_page.save_current_setup_dialog(self.get_toplevel())
            if saved:
                self._refresh_user_profile_rows()
            return
        # No AutoPilot page (shouldn't happen): fall back to upstream behavior.
        for profile in self._device.profiles:
            if not profile.disabled:
                continue
            profile.disabled = False
            break

    def _on_profile_notify_disabled(
        self, profile: RatbagdProfile, pspec: Optional[GObject.ParamSpec]
    ) -> None:
        assert self._device is not None

        # Always sensitive in this fork: the button creates user profiles.
        self.add_profile_button.set_sensitive(True)

    def _on_profile_notify_dirty(
        self, profile: RatbagdProfile, pspec: Optional[GObject.ParamSpec]
    ) -> None:
        assert self._device is not None

        device_dirty = any(p.dirty for p in self._device.profiles)

        style_context = self.button_commit.get_style_context()
        if device_dirty:
            style_context.add_class("suggested-action")
            self.button_commit.set_sensitive(True)
        else:
            # There is no way to make a single profile non-dirty, so this works
            # for now. Ideally, this should however check if there are any other
            # profiles on the device that are dirty.
            style_context.remove_class("suggested-action")
            self.button_commit.set_sensitive(False)

    def shutdown(self) -> None:
        """Release resources held by this perspective.

        Called by Window when the application window is destroyed. This cannot
        be a delete-event handler: that signal is only emitted on toplevels,
        and this perspective is a Gtk.Overlay nested inside the window.
        """
        if self._autopilot_page is not None:
            self._autopilot_page.shutdown()
