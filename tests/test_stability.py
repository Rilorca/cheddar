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


class TestFaugusIntegration(unittest.TestCase):
    """Unit tests for Faugus launcher game detection and AutoPilot profile switching."""

    def test_faugus_discovery_if_present(self):
        """If Faugus is installed on the system (e.g. user has Battle.net with WoW & HotS),
        verify they are properly detected with the right executables."""
        from cheddar.autopilot_games import installed_games

        games_by_name = {g.name: g for g in installed_games()}
        # If user has Battle.net / WoW / HotS installed via Faugus on this machine:
        if "World of Warcraft" in games_by_name:
            wow = games_by_name["World of Warcraft"]
            self.assertEqual(wow.source, "Faugus")
            self.assertEqual(wow.exe, "wow.exe")
            self.assertTrue(wow.icon and os.path.isfile(wow.icon))

        if "Heroes of the Storm" in games_by_name:
            hots = games_by_name["Heroes of the Storm"]
            self.assertEqual(hots.source, "Faugus")
            self.assertIn("heroes of the storm", hots.exe)
            self.assertTrue(hots.icon and os.path.isfile(hots.icon))

        if "Battle.net" in games_by_name:
            bnet = games_by_name["Battle.net"]
            self.assertEqual(bnet.source, "Faugus")
            self.assertEqual(bnet.exe, "battle.net.exe")

    def test_faugus_mocked_prefix_scanning(self):
        """Test _scan_faugus with a mock Faugus configuration and Wine prefix."""
        import json
        import tempfile
        from cheddar.autopilot_games import _scan_faugus

        with tempfile.TemporaryDirectory() as tmpdir:
            faugus_root = os.path.join(tmpdir, "faugus")
            prefix_dir = os.path.join(tmpdir, "prefix")
            shortcuts_dir = os.path.join(prefix_dir, "drive_c", "proton_shortcuts")
            icons_dir = os.path.join(shortcuts_dir, "icons", "256x256", "apps")
            game_install_dir = os.path.join(prefix_dir, "drive_c", "Program Files (x86)", "Test Game")

            os.makedirs(faugus_root)
            os.makedirs(icons_dir)
            os.makedirs(game_install_dir)

            # Create dummy game executable (>100KB so _find_game_exe accepts it)
            game_exe = os.path.join(game_install_dir, "TestGame.exe")
            with open(game_exe, "wb") as f:
                f.write(b"\0" * (120 * 1024))

            # Create dummy icon
            icon_file = os.path.join(icons_dir, "testgame_icon.png")
            with open(icon_file, "wb") as f:
                f.write(b"\0" * 100)

            # Create proton_shortcuts desktop file
            desktop_content = (
                f"[Desktop Entry]\n"
                f"Name=Test Game\n"
                f"Path={game_install_dir}\n"
                f"Icon=testgame_icon\n"
                f"StartupWMClass=testgame.exe\n"
            )
            with open(os.path.join(shortcuts_dir, "Test Game.desktop"), "w") as f:
                f.write(desktop_content)

            # Create games.json
            games_json_data = [
                {
                    "gameid": "test_game",
                    "title": "Test Game",
                    "path": game_exe,
                    "prefix": prefix_dir,
                    "icon": icon_file,
                }
            ]
            with open(os.path.join(faugus_root, "games.json"), "w") as f:
                json.dump(games_json_data, f)

            with patch("cheddar.autopilot_games._FAUGUS_ROOTS", (faugus_root,)):
                scanned = _scan_faugus()
                self.assertEqual(len(scanned), 1)
                self.assertEqual(scanned[0].name, "Test Game")
                self.assertEqual(scanned[0].exe, "testgame.exe")
                self.assertEqual(scanned[0].source, "Faugus")
                self.assertEqual(scanned[0].icon, icon_file)

    def test_watcher_hots_matching_with_spaces_and_arch(self):
        """Test AutoPilotWatcher matching for Heroes of the Storm when process is
        HeroesOfTheStorm_x64.exe and rule is 'heroes of the storm.exe'."""
        from cheddar.autopilot_watcher import AutoPilotWatcher, _add_name

        names = set()
        _add_name(names, "HeroesOfTheStorm_x64.exe")

        self.assertIn("heroesofthestorm_x64.exe", names)
        self.assertIn("heroesofthestorm_x64", names)
        self.assertIn("heroesofthestorm.exe", names)
        self.assertIn("heroesofthestorm", names)

        proc_map = {9999: names}
        switches = []
        watcher = AutoPilotWatcher(
            rules={"heroes of the storm.exe": 2},
            on_switch=lambda p, l: switches.append((p, l)),
            default_profile=0,
        )

        with patch("cheddar.autopilot_watcher._scan_processes", return_value=proc_map), \
             patch("cheddar.autopilot_watcher._focused_pid", return_value=9999):
            watcher._tick()

        self.assertEqual(watcher._active_profile, 2)


if __name__ == "__main__":
    unittest.main()

