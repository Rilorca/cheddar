# SPDX-License-Identifier: GPL-2.0-or-later

import unittest
from unittest.mock import MagicMock, patch

from cheddar.autopilot_service import (
    SERVICE_NAME,
    is_daemon_service_active,
    is_daemon_service_enabled,
    start_daemon_service,
    stop_daemon_service,
)


class TestAutoPilotService(unittest.TestCase):
    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("subprocess.run")
    def test_is_daemon_service_active_true(self, mock_run, _mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="active\n")
        self.assertTrue(is_daemon_service_active())
        mock_run.assert_called_once_with(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            stdout=-1,
            stderr=-3,
            text=True,
            timeout=1.0,
        )

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("subprocess.run")
    def test_is_daemon_service_active_inactive(self, mock_run, _mock_which):
        mock_run.return_value = MagicMock(returncode=3, stdout="inactive\n")
        self.assertFalse(is_daemon_service_active())

    @patch("shutil.which", return_value=None)
    def test_is_daemon_service_active_no_systemctl(self, _mock_which):
        self.assertFalse(is_daemon_service_active())

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("subprocess.run")
    def test_is_daemon_service_enabled_true(self, mock_run, _mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="enabled\n")
        self.assertTrue(is_daemon_service_enabled())

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("subprocess.run")
    def test_start_daemon_service(self, mock_run, _mock_which):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(start_daemon_service())
        mock_run.assert_called_once_with(
            ["systemctl", "--user", "start", SERVICE_NAME],
            stdout=-3,
            stderr=-3,
            timeout=3.0,
        )

    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("subprocess.run")
    def test_stop_daemon_service(self, mock_run, _mock_which):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(stop_daemon_service())
        mock_run.assert_called_once_with(
            ["systemctl", "--user", "stop", SERVICE_NAME],
            stdout=-3,
            stderr=-3,
            timeout=3.0,
        )

    def test_live_systemd_check(self):
        # Checks against the real environment without crashing
        status = is_daemon_service_active()
        self.assertIsInstance(status, bool)


if __name__ == "__main__":
    unittest.main()
