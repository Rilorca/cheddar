# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import gi

gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, GObject, Gtk  # noqa

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cheddar import autostart
from cheddar.autopilot_watcher import AutoPilotWatcher
from cheddar.ratbagd import RatbagdDevice, RatbagdProfile


class TestRatbagdStability(unittest.TestCase):
    """Unit tests verifying that ratbagd edge-cases (like None index) do not crash."""

    def test_active_profile_changed_with_none_index(self):
        """Verify that _on_active_profile_changed does not throw TypeError when
        profile.index is None (regression test for bug causing Cheddar exit)."""

        # Mock RatbagdDevice and RatbagdProfile
        mock_device = MagicMock(spec=RatbagdDevice)
        mock_device._profiles = [MagicMock(spec=RatbagdProfile), MagicMock(spec=RatbagdProfile)]
        mock_device.emit = MagicMock()

        # Create a mock profile where index is None
        mock_profile = MagicMock(spec=RatbagdProfile)
        mock_profile.is_active = True
        mock_profile.index = None

        # Call the actual method from RatbagdDevice
        RatbagdDevice._on_active_profile_changed(mock_device, mock_profile, None)

        # Should emit with the profile fallback, NOT raise TypeError
        mock_device.emit.assert_called_once_with("active-profile-changed", mock_profile)

    def test_active_profile_changed_with_valid_index(self):
        """Verify that _on_active_profile_changed properly indexes when index is valid."""
        mock_device = MagicMock(spec=RatbagdDevice)
        p0 = MagicMock(spec=RatbagdProfile)
        p1 = MagicMock(spec=RatbagdProfile)
        mock_device._profiles = [p0, p1]
        mock_device.emit = MagicMock()

        mock_profile = MagicMock(spec=RatbagdProfile)
        mock_profile.is_active = True
        mock_profile.index = 1

        RatbagdDevice._on_active_profile_changed(mock_device, mock_profile, None)
        mock_device.emit.assert_called_once_with("active-profile-changed", p1)

    def test_active_profile_changed_with_out_of_bounds_index(self):
        """Verify that _on_active_profile_changed handles out-of-bounds index safely."""
        mock_device = MagicMock(spec=RatbagdDevice)
        p0 = MagicMock(spec=RatbagdProfile)
        mock_device._profiles = [p0]
        mock_device.emit = MagicMock()

        mock_profile = MagicMock(spec=RatbagdProfile)
        mock_profile.is_active = True
        mock_profile.index = 99

        RatbagdDevice._on_active_profile_changed(mock_device, mock_profile, None)
        mock_device.emit.assert_called_once_with("active-profile-changed", mock_profile)


class TestAutostart(unittest.TestCase):
    """Unit tests for XDG autostart configuration."""

    def test_enable_and_disable_autostart(self):
        """Test enabling and disabling autostart file generation."""
        # Enable autostart
        self.assertTrue(autostart.set_autostart_enabled(True))
        self.assertTrue(autostart.is_autostart_enabled())

        autostart_path = autostart._get_autostart_path()
        self.assertTrue(os.path.isfile(autostart_path))

        with open(autostart_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[Desktop Entry]", content)
        self.assertIn("--background", content)
        self.assertIn("X-GNOME-Autostart-enabled=true", content)

        # Disable autostart
        self.assertTrue(autostart.set_autostart_enabled(False))
        self.assertFalse(autostart.is_autostart_enabled())
        self.assertFalse(os.path.isfile(autostart_path))


class TestAutoPilotWatcherStability(unittest.TestCase):
    """Unit tests for AutoPilotWatcher exception resilience."""

    def test_watcher_tick_exception_resilience(self):
        """Ensure that an unexpected exception during tick does not crash the loop."""
        callback = MagicMock()
        watcher = AutoPilotWatcher(rules={"game.exe": 1}, on_switch=callback)

        # Force _tick to raise an exception
        with patch.object(watcher, "_tick", side_effect=RuntimeError("Simulated proc error")):
            # Running loop for one tick iteration via event timeout
            watcher._stop_event.set()
            # _loop should complete without uncaught exception
            watcher._loop()

        self.assertFalse(watcher.is_running())


if __name__ == "__main__":
    unittest.main()
