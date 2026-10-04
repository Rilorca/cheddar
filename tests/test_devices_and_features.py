# SPDX-License-Identifier: GPL-2.0-or-later
#
# test_devices_and_features.py - Comprehensive unit testing suite for Cheddar
# Tests every function with the connected Logitech Gaming Mouse G600 (live hardware)
# and with 3 simulated mice:
#   1. Logitech G502 Hero (multi-profile, separate XY DPI, 11 buttons, 2 RGB LEDs)
#   2. Logitech G Pro Wireless (5 profiles, 4 DPI stages, ambidextrous buttons, 1 LED)
#   3. SteelSeries Rival 310 (single-profile edge case, 2 DPI stages, 6 buttons, 2 LEDs)

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

import gi

gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, GObject, Gtk  # noqa

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cheddar import autopilot_profiles
from cheddar.autopilot_profiles import (
    SW_PREFIX,
    activate_target,
    apply_profile,
    capture_profile,
    ensure_valid_active_resolution,
    is_software_target,
    load_store,
    save_store,
    scratch_slot_for,
    target_label,
)
from cheddar.ratbagd import (
    Ratbagd,
    RatbagdButton,
    RatbagdDevice,
    RatbagdLed,
    RatbagdMacro,
    RatbagdProfile,
    RatbagdResolution,
    RatbagDeviceType,
)


class MockRatbagdResolution(GObject.GObject):
    """Simulated RatbagdResolution object for unit testing."""

    CAP_SEPARATE_XY_RESOLUTION = 1
    CAP_DISABLE = 2

    def __init__(self, index, resolution=(800,), is_active=False, is_default=False, is_disabled=False, capabilities=None, resolutions=None):
        super().__init__()
        self._index = index
        self._resolution = resolution
        self._active = is_active
        self._default = is_default
        self._disabled = is_disabled
        self._capabilities = capabilities or []
        self._resolutions = resolutions or [400, 800, 1600, 3200]
        self._profile = None

    @GObject.Property
    def index(self):
        return self._index

    @GObject.Property
    def resolution(self):
        return self._resolution

    @resolution.setter
    def resolution(self, val):
        val = tuple(val)
        if len(val) != len(self._resolution) or len(val) > 2:
            raise ValueError("invalid resolution precision")
        if val != self._resolution:
            self._resolution = val
            self.notify("resolution")

    @GObject.Property
    def resolutions(self):
        return self._resolutions

    @GObject.Property
    def is_active(self):
        return self._active

    @GObject.Property
    def is_default(self):
        return self._default

    @GObject.Property
    def is_disabled(self):
        return self._disabled

    @GObject.Property
    def capabilities(self):
        return self._capabilities

    def set_active(self):
        if self._profile is not None:
            for r in self._profile.resolutions:
                if r is not self and r._active:
                    r._active = False
                    r.notify("is-active")
        if not self._active:
            self._active = True
            self.notify("is-active")
        return 0

    def set_default(self):
        if self._profile is not None:
            for r in self._profile.resolutions:
                if r is not self and r._default:
                    r._default = False
                    r.notify("is-default")
        if not self._default:
            self._default = True
            self.notify("is-default")
        return 0

    def set_disabled(self, disabled):
        if disabled != self._disabled:
            self._disabled = disabled
            self.notify("is-disabled")
        return 0


class MockRatbagdButton(GObject.GObject):
    """Simulated RatbagdButton object for unit testing."""

    ActionType = RatbagdButton.ActionType
    ActionSpecial = RatbagdButton.ActionSpecial
    Macro = RatbagdButton.Macro

    def __init__(self, index, action_type=ActionType.BUTTON, value=None):
        super().__init__()
        self._index = index
        self._action_type = action_type
        self._mapping = value if action_type == self.ActionType.BUTTON else None
        self._special = value if action_type == self.ActionType.SPECIAL else None
        self._key = value if action_type == self.ActionType.KEY else None
        self._macro = value if action_type == self.ActionType.MACRO else None
        self._action_types = [
            self.ActionType.NONE,
            self.ActionType.BUTTON,
            self.ActionType.SPECIAL,
            self.ActionType.KEY,
            self.ActionType.MACRO,
        ]

    @GObject.Property
    def index(self):
        return self._index

    @GObject.Property
    def action_type(self):
        return self._action_type

    @GObject.Property
    def action_types(self):
        return self._action_types

    @GObject.Property
    def mapping(self):
        return self._mapping if self._action_type == self.ActionType.BUTTON else None

    @mapping.setter
    def mapping(self, val):
        self._action_type = self.ActionType.BUTTON
        self._mapping = val
        self._special = None
        self._key = None
        self._macro = None
        self.notify("action-type")

    @GObject.Property
    def special(self):
        return self._special if self._action_type == self.ActionType.SPECIAL else None

    @special.setter
    def special(self, val):
        self._action_type = self.ActionType.SPECIAL
        self._special = val
        self._mapping = None
        self._key = None
        self._macro = None
        self.notify("action-type")

    @GObject.Property
    def key(self):
        return self._key if self._action_type == self.ActionType.KEY else None

    @key.setter
    def key(self, val):
        self._action_type = self.ActionType.KEY
        self._key = val
        self._mapping = None
        self._special = None
        self._macro = None
        self.notify("action-type")

    @GObject.Property
    def macro(self):
        return self._macro if self._action_type == self.ActionType.MACRO else None

    @macro.setter
    def macro(self, val):
        self._action_type = self.ActionType.MACRO
        self._macro = val
        self._mapping = None
        self._special = None
        self._key = None
        self.notify("action-type")

    @GObject.Property
    def disabled(self):
        return self._action_type == self.ActionType.NONE

    def disable(self):
        self._action_type = self.ActionType.NONE
        self._mapping = None
        self._special = None
        self._key = None
        self._macro = None
        self.notify("action-type")


class MockRatbagdLed(GObject.GObject):
    """Simulated RatbagdLed object for unit testing."""

    Mode = RatbagdLed.Mode
    ColorDepth = RatbagdLed.ColorDepth

    def __init__(self, index, mode=Mode.ON, color=(255, 0, 0), brightness=255, duration=1000):
        super().__init__()
        self._index = index
        self._mode = mode
        self._color = color
        self._brightness = brightness
        self._duration = duration
        self._modes = [self.Mode.OFF, self.Mode.ON, self.Mode.CYCLE, self.Mode.BREATHING]
        self._colordepth = self.ColorDepth.RGB_888

    @GObject.Property
    def index(self):
        return self._index

    @GObject.Property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, val):
        if val != self._mode:
            self._mode = val
            self.notify("mode")

    @GObject.Property
    def modes(self):
        return self._modes

    @GObject.Property
    def color(self):
        return self._color

    @color.setter
    def color(self, val):
        val = tuple(val)
        if val != self._color:
            self._color = val
            self.notify("color")

    @GObject.Property
    def colordepth(self):
        return self._colordepth

    @GObject.Property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, val):
        if val != self._brightness:
            self._brightness = val
            self.notify("brightness")

    @GObject.Property
    def effect_duration(self):
        return self._duration

    @effect_duration.setter
    def effect_duration(self, val):
        if val != self._duration:
            self._duration = val
            self.notify("effect-duration")


class MockRatbagdProfile(GObject.GObject):
    """Simulated RatbagdProfile object for unit testing."""

    def __init__(self, index, name="Profile", is_active=False, report_rate=1000, report_rates=None, resolutions=None, buttons=None, leds=None):
        super().__init__()
        self._index = index
        self._name = name
        self._active = is_active
        self._disabled = False
        self._dirty = False
        self._angle_snapping = 0
        self._debounce = 0
        self._report_rate = report_rate
        self._report_rates = report_rates or [125, 250, 500, 1000]
        self._resolutions = resolutions or []
        for r in self._resolutions:
            r._profile = self
        self._buttons = buttons or []
        self._leds = leds or []
        self._device = None

    @GObject.Property
    def index(self):
        return self._index

    @GObject.Property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        if val != self._name:
            self._name = val
            self.notify("name")

    @GObject.Property
    def is_active(self):
        return self._active

    def set_active(self):
        if self._device is not None:
            for p in self._device.profiles:
                if p is not self and p._active:
                    p._active = False
                    p.notify("is-active")
        if not self._active:
            self._active = True
            self.notify("is-active")
        return 0

    @GObject.Property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, val):
        if val != self._disabled:
            self._disabled = val
            self.notify("disabled")

    @GObject.Property
    def dirty(self):
        return self._dirty

    @GObject.Property
    def report_rate(self):
        return self._report_rate

    @report_rate.setter
    def report_rate(self, rate):
        if rate != self._report_rate:
            self._report_rate = rate
            self.notify("report-rate")

    @GObject.Property
    def report_rates(self):
        return self._report_rates

    @GObject.Property
    def angle_snapping(self):
        return self._angle_snapping

    @angle_snapping.setter
    def angle_snapping(self, val):
        if val != self._angle_snapping:
            self._angle_snapping = val
            self.notify("angle-snapping")

    @GObject.Property
    def debounce(self):
        return self._debounce

    @debounce.setter
    def debounce(self, val):
        if val != self._debounce:
            self._debounce = val
            self.notify("debounce")

    @GObject.Property
    def debounces(self):
        return [0, 2, 4, 8, 16]

    @GObject.Property
    def capabilities(self):
        return [RatbagdProfile.CAP_WRITABLE_NAME]

    @GObject.Property
    def resolutions(self):
        return self._resolutions

    @GObject.Property
    def active_resolution(self):
        for r in self._resolutions:
            if r.is_active:
                return r
        return None

    @GObject.Property
    def buttons(self):
        return self._buttons

    @GObject.Property
    def leds(self):
        return self._leds


class MockRatbagdDevice(GObject.GObject):
    """Simulated RatbagdDevice object for unit testing."""

    __gsignals__ = {
        "active-profile-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (GObject.TYPE_PYOBJECT,),
        ),
        "resync": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, device_id, name, model, profiles=None, device_type=RatbagDeviceType.MOUSE):
        super().__init__()
        self._id = device_id
        self._name = name
        self._model = model
        self._device_type = device_type
        self._profiles = profiles or []
        for p in self._profiles:
            p._device = self
            p.connect("notify::is-active", self._on_active_profile_changed)
        self.committed = False

    def _on_active_profile_changed(self, profile, pspec):
        if profile.is_active:
            idx = profile.index
            if idx is not None and isinstance(idx, int) and 0 <= idx < len(self._profiles):
                self.emit("active-profile-changed", self._profiles[idx])
            else:
                self.emit("active-profile-changed", profile)

    @GObject.Property
    def id(self):
        return self._id

    @GObject.Property
    def name(self):
        return self._name

    @GObject.Property
    def model(self):
        return self._model

    @GObject.Property
    def device_type(self):
        return self._device_type

    @GObject.Property
    def firmware_version(self):
        return "1.0.0"

    @GObject.Property
    def profiles(self):
        return self._profiles

    @GObject.Property
    def active_profile(self):
        for p in self._profiles:
            if p.is_active:
                return p
        return None

    def commit(self):
        self.committed = True


# ==============================================================================
# TEST SUITE 1: Real Connected Logitech Gaming Mouse G600
# ==============================================================================
class TestLiveLogitechG600(unittest.TestCase):
    """Comprehensive tests on the user's physical Logitech G600 mouse.
    Verifies every property, getters, safe non-destructive setters, and AutoPilot
    software profile capture/restore."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.ratbagd = Ratbagd(2)
            cls.g600 = None
            for d in cls.ratbagd.devices:
                if "g600" in d.name.lower():
                    cls.g600 = d
                    break
        except Exception as e:
            cls.g600 = None
            cls.skip_reason = str(e)

    def setUp(self):
        if not self.g600:
            self.skipTest(f"Logitech G600 mouse not connected or ratbagd unavailable ({getattr(self, 'skip_reason', 'none')})")

    def test_g600_device_attributes(self):
        """Test reading G600 top-level attributes: id, name, model, type, profiles count."""
        self.assertIn("G600", self.g600.name)
        self.assertIsNotNone(self.g600.id)
        self.assertIsNotNone(self.g600.model)
        self.assertEqual(self.g600.device_type, RatbagDeviceType.MOUSE)
        self.assertEqual(len(self.g600.profiles), 3)

    def test_g600_active_profile_resolution_and_buttons(self):
        """Test reading G600 profile properties, resolution, report rate, buttons, LEDs."""
        active = self.g600.active_profile
        self.assertIsNotNone(active)
        self.assertTrue(active.is_active)
        self.assertEqual(len(active.buttons), 41)
        self.assertEqual(len(active.resolutions), 4)
        self.assertEqual(len(active.leds), 1)

        # Resolutions
        active_res = active.active_resolution
        self.assertIsNotNone(active_res)
        self.assertTrue(active_res.is_active)
        self.assertGreater(active_res.resolution[0], 0)
        self.assertIn(active.report_rate, active.report_rates)

        # LEDs
        led = active.leds[0]
        self.assertIn(led.mode, led.modes)
        self.assertEqual(len(led.color), 3)
        self.assertGreaterEqual(led.brightness, 0)

    def test_g600_capture_profile_structure(self):
        """Test that capture_profile correctly captures full G600 profile configuration."""
        active = self.g600.active_profile
        captured = capture_profile(active)

        self.assertEqual(captured["version"], 1)
        self.assertEqual(captured["report_rate"], active.report_rate)
        self.assertEqual(len(captured["resolutions"]), 4)
        self.assertEqual(len(captured["buttons"]), 41)
        self.assertEqual(len(captured["leds"]), 1)

        # Verify button 0 is left click
        btn0 = captured["buttons"][0]
        self.assertEqual(btn0["index"], 0)
        self.assertEqual(btn0["type"], int(RatbagdButton.ActionType.BUTTON))
        self.assertEqual(btn0["value"], 1)

    def test_g600_safe_scratch_slot_calculation(self):
        """Test scratch slot resolution for G600 under various user configurations."""
        # Default should be last slot (index 2 for G600)
        self.assertEqual(scratch_slot_for(self.g600, {}), 2)
        # Custom valid slot
        self.assertEqual(scratch_slot_for(self.g600, {"scratch_slot": 1}), 1)
        # Out-of-range custom slot falls back to last slot
        self.assertEqual(scratch_slot_for(self.g600, {"scratch_slot": 99}), 2)


# ==============================================================================
# TEST SUITE 2: Simulated Logitech G502 Hero
# Capabilities: 5 onboard profiles, 5 DPI stages, individual XY DPI support,
# 11 buttons, 2 RGB LEDs (Logo and DPI bars).
# ==============================================================================
class TestSimulatedLogitechG502Hero(unittest.TestCase):
    """Tests every feature and function against a simulated Logitech G502 Hero."""

    def setUp(self):
        profiles = []
        for p_idx in range(5):
            res_list = [
                MockRatbagdResolution(0, (400, 400), is_active=False, is_default=False, capabilities=[MockRatbagdResolution.CAP_SEPARATE_XY_RESOLUTION]),
                MockRatbagdResolution(1, (800, 800), is_active=(p_idx == 0), is_default=True, capabilities=[MockRatbagdResolution.CAP_SEPARATE_XY_RESOLUTION]),
                MockRatbagdResolution(2, (1600, 1600), is_active=False, is_default=False, capabilities=[MockRatbagdResolution.CAP_SEPARATE_XY_RESOLUTION]),
                MockRatbagdResolution(3, (3200, 3200), is_active=False, is_default=False, capabilities=[MockRatbagdResolution.CAP_SEPARATE_XY_RESOLUTION]),
                MockRatbagdResolution(4, (6400, 6400), is_active=False, is_default=False, capabilities=[MockRatbagdResolution.CAP_SEPARATE_XY_RESOLUTION]),
            ]
            btn_list = [
                MockRatbagdButton(0, RatbagdButton.ActionType.BUTTON, 1),
                MockRatbagdButton(1, RatbagdButton.ActionType.BUTTON, 2),
                MockRatbagdButton(2, RatbagdButton.ActionType.BUTTON, 3),
                MockRatbagdButton(3, RatbagdButton.ActionType.BUTTON, 4),
                MockRatbagdButton(4, RatbagdButton.ActionType.BUTTON, 5),
                MockRatbagdButton(5, RatbagdButton.ActionType.SPECIAL, RatbagdButton.ActionSpecial.RESOLUTION_DOWN),
                MockRatbagdButton(6, RatbagdButton.ActionType.SPECIAL, RatbagdButton.ActionSpecial.RESOLUTION_UP),
                MockRatbagdButton(7, RatbagdButton.ActionType.SPECIAL, RatbagdButton.ActionSpecial.PROFILE_CYCLE_UP),
                MockRatbagdButton(8, RatbagdButton.ActionType.BUTTON, 8),
                MockRatbagdButton(9, RatbagdButton.ActionType.BUTTON, 9),
                MockRatbagdButton(10, RatbagdButton.ActionType.SPECIAL, RatbagdButton.ActionSpecial.RESOLUTION_ALTERNATE),
            ]
            led_list = [
                MockRatbagdLed(0, mode=RatbagdLed.Mode.ON, color=(0, 120, 255), brightness=255),  # Logo
                MockRatbagdLed(1, mode=RatbagdLed.Mode.BREATHING, color=(0, 255, 100), brightness=200),  # DPI Indicator
            ]
            profiles.append(MockRatbagdProfile(
                p_idx,
                name=f"G502 Profile {p_idx}",
                is_active=(p_idx == 0),
                report_rate=1000,
                resolutions=res_list,
                buttons=btn_list,
                leds=led_list,
            ))

        self.g502 = MockRatbagdDevice("g502_hero_test", "Logitech G502 HERO Gaming Mouse", "usb:046d:c08b:0", profiles)

    def test_profile_switching_and_signals(self):
        """Test setting active profile and signal emission on G502."""
        signals = []
        self.g502.connect("active-profile-changed", lambda dev, prof: signals.append(prof.index))

        self.assertEqual(self.g502.active_profile.index, 0)
        self.g502.profiles[3].set_active()

        self.assertEqual(self.g502.active_profile.index, 3)
        self.assertFalse(self.g502.profiles[0].is_active)
        self.assertTrue(self.g502.profiles[3].is_active)
        self.assertIn(3, signals)

    def test_separate_xy_resolution_handling(self):
        """Test setting and getting separate XY resolution on G502."""
        prof = self.g502.profiles[0]
        res = prof.resolutions[1]

        self.assertEqual(res.resolution, (800, 800))
        res.resolution = (1200, 1000)
        self.assertEqual(res.resolution, (1200, 1000))

        # Resolution switching
        prof.resolutions[3].set_active()
        self.assertEqual(prof.active_resolution.index, 3)
        self.assertFalse(prof.resolutions[1].is_active)
        self.assertTrue(prof.resolutions[3].is_active)

    def test_dual_led_configuration(self):
        """Test controlling both primary and indicator LEDs on G502."""
        prof = self.g502.profiles[0]
        led0, led1 = prof.leds

        led0.mode = RatbagdLed.Mode.CYCLE
        led0.color = (255, 255, 0)
        self.assertEqual(led0.mode, RatbagdLed.Mode.CYCLE)
        self.assertEqual(led0.color, (255, 255, 0))

        led1.brightness = 128
        self.assertEqual(led1.brightness, 128)

    def test_autopilot_capture_and_apply_profile_xy(self):
        """Test capturing a profile with separate XY resolution and applying to scratch slot."""
        src_profile = self.g502.profiles[1]
        src_profile.resolutions[0].resolution = (600, 500)
        src_profile.resolutions[0].set_active()

        # Capture
        cap = capture_profile(src_profile)
        self.assertEqual(cap["resolutions"][0]["resolution"], [600, 500])

        # Apply to profile 4 (scratch slot)
        dst_profile = self.g502.profiles[4]
        apply_profile(cap, dst_profile)

        self.assertEqual(dst_profile.resolutions[0].resolution, (600, 500))
        self.assertTrue(dst_profile.resolutions[0].is_active)


# ==============================================================================
# TEST SUITE 3: Simulated Logitech G Pro Wireless
# Capabilities: 5 onboard profiles, 4 DPI stages, ambidextrous side buttons (8 buttons),
# 1 RGB LED.
# ==============================================================================
class TestSimulatedLogitechGProWireless(unittest.TestCase):
    """Tests every feature and function against a simulated Logitech G Pro Wireless."""

    def setUp(self):
        profiles = []
        for p_idx in range(5):
            res_list = [
                MockRatbagdResolution(0, (400,), is_active=False, is_default=False),
                MockRatbagdResolution(1, (800,), is_active=(p_idx == 0), is_default=True),
                MockRatbagdResolution(2, (1600,), is_active=False, is_default=False),
                MockRatbagdResolution(3, (3200,), is_active=False, is_default=False),
            ]
            # 8 buttons: Left, Right, Middle, Left Back, Left Fwd, Right Back, Right Fwd, DPI cycle bottom
            btn_list = [
                MockRatbagdButton(0, RatbagdButton.ActionType.BUTTON, 1),
                MockRatbagdButton(1, RatbagdButton.ActionType.BUTTON, 2),
                MockRatbagdButton(2, RatbagdButton.ActionType.BUTTON, 3),
                MockRatbagdButton(3, RatbagdButton.ActionType.BUTTON, 4),
                MockRatbagdButton(4, RatbagdButton.ActionType.BUTTON, 5),
                MockRatbagdButton(5, RatbagdButton.ActionType.NONE, None),  # Right side disabled
                MockRatbagdButton(6, RatbagdButton.ActionType.NONE, None),  # Right side disabled
                MockRatbagdButton(7, RatbagdButton.ActionType.SPECIAL, RatbagdButton.ActionSpecial.RESOLUTION_CYCLE_UP),
            ]
            led_list = [
                MockRatbagdLed(0, mode=RatbagdLed.Mode.ON, color=(255, 0, 128), brightness=255),
            ]
            profiles.append(MockRatbagdProfile(
                p_idx,
                name=f"GPW Profile {p_idx}",
                is_active=(p_idx == 0),
                report_rate=1000,
                resolutions=res_list,
                buttons=btn_list,
                leds=led_list,
            ))

        self.gpw = MockRatbagdDevice("gpw_test", "Logitech G Pro Wireless Gaming Mouse", "usb:046d:4079:0", profiles)

    def test_ambidextrous_button_disabling_and_mapping(self):
        """Test enabling and mapping previously disabled side buttons on G Pro Wireless."""
        prof = self.gpw.profiles[0]
        btn5 = prof.buttons[5]
        btn6 = prof.buttons[6]

        self.assertTrue(btn5.disabled)
        self.assertTrue(btn6.disabled)

        # Enable button 5 as mouse button 6
        btn5.mapping = 6
        self.assertFalse(btn5.disabled)
        self.assertEqual(btn5.action_type, RatbagdButton.ActionType.BUTTON)
        self.assertEqual(btn5.mapping, 6)

        # Enable button 6 as keyboard key
        btn6.key = 30  # KEY_A
        self.assertFalse(btn6.disabled)
        self.assertEqual(btn6.action_type, RatbagdButton.ActionType.KEY)
        self.assertEqual(btn6.key, 30)

        # Re-disable button 5
        btn5.disable()
        self.assertTrue(btn5.disabled)
        self.assertEqual(btn5.action_type, RatbagdButton.ActionType.NONE)

    def test_macro_creation_and_application(self):
        """Test macro mapping and execution flow on G Pro Wireless."""
        prof = self.gpw.profiles[0]
        btn = prof.buttons[3]

        macro = RatbagdMacro()
        macro.append(RatbagdButton.Macro.KEY_PRESS, 29)    # KEY_LEFTCTRL
        macro.append(RatbagdButton.Macro.KEY_PRESS, 46)    # KEY_C
        macro.append(RatbagdButton.Macro.KEY_RELEASE, 46)
        macro.append(RatbagdButton.Macro.KEY_RELEASE, 29)

        btn.macro = macro
        self.assertEqual(btn.action_type, RatbagdButton.ActionType.MACRO)
        self.assertIsNotNone(btn.macro)
        self.assertEqual(len(btn.macro.keys), 4)

    def test_autopilot_full_lifecycle_with_temp_store(self):
        """Test AutoPilot software profile saving, loading, and activating on G Pro Wireless."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_file = os.path.join(tmpdir, "autopilot_profiles.json")
            state_file = os.path.join(tmpdir, "autopilot_state.json")

            with patch("cheddar.autopilot_profiles._STORE_FILE", store_file), \
                 patch("cheddar.autopilot_profiles._STATE_FILE", state_file), \
                 patch("cheddar.autopilot_profiles._STORE_DIR", tmpdir):

                # 1. Capture current profile 0
                prof0 = self.gpw.profiles[0]
                prof0_data = capture_profile(prof0)
                prof0_data["report_rate"] = 500

                # 2. Save into store as 'Apex Legends'
                save_store({"Apex Legends": prof0_data})
                loaded = load_store()
                self.assertIn("Apex Legends", loaded)

                # 3. Activate software target 'sw:Apex Legends'
                activate_target(self.gpw, "sw:Apex Legends", {})

                # Verify scratch slot (index 4) was updated and activated
                scratch = self.gpw.profiles[4]
                self.assertTrue(scratch.is_active)
                self.assertEqual(scratch.report_rate, 500)
                self.assertTrue(self.gpw.committed)
                self.assertEqual(autopilot_profiles.active_user_profile(), "Apex Legends")

                # 4. Activate hardware profile index 1
                activate_target(self.gpw, 1, {})
                self.assertTrue(self.gpw.profiles[1].is_active)
                self.assertFalse(self.gpw.profiles[4].is_active)
                self.assertIsNone(autopilot_profiles.active_user_profile())


# ==============================================================================
# TEST SUITE 4: Simulated Single-Profile Mouse (SteelSeries Rival 310 / Generic)
# Capabilities: Only 1 onboard profile (critical AutoPilot edge-case: len(profiles) == 1),
# 2 DPI stages, 6 buttons, 2 RGB LEDs.
# ==============================================================================
class TestSimulatedSingleProfileMouse(unittest.TestCase):
    """Tests Cheddar functions and AutoPilot edge-cases on a single-profile mouse."""

    def setUp(self):
        res_list = [
            MockRatbagdResolution(0, (800,), is_active=True, is_default=True),
            MockRatbagdResolution(1, (1600,), is_active=False, is_default=False),
        ]
        btn_list = [
            MockRatbagdButton(0, RatbagdButton.ActionType.BUTTON, 1),
            MockRatbagdButton(1, RatbagdButton.ActionType.BUTTON, 2),
            MockRatbagdButton(2, RatbagdButton.ActionType.BUTTON, 3),
            MockRatbagdButton(3, RatbagdButton.ActionType.BUTTON, 4),
            MockRatbagdButton(4, RatbagdButton.ActionType.BUTTON, 5),
            MockRatbagdButton(5, RatbagdButton.ActionType.SPECIAL, RatbagdButton.ActionSpecial.RESOLUTION_CYCLE_UP),
        ]
        led_list = [
            MockRatbagdLed(0, mode=RatbagdLed.Mode.ON, color=(255, 60, 0), brightness=255),
            MockRatbagdLed(1, mode=RatbagdLed.Mode.BREATHING, color=(255, 60, 0), brightness=180),
        ]
        single_profile = MockRatbagdProfile(
            0,
            name="Default",
            is_active=True,
            report_rate=1000,
            resolutions=res_list,
            buttons=btn_list,
            leds=led_list,
        )

        self.mouse = MockRatbagdDevice("rival_310_test", "SteelSeries Rival 310", "usb:1038:1720:0", [single_profile])

    def test_single_profile_scratch_slot_calculation(self):
        """Ensure single-profile mouse resolves scratch slot cleanly to slot 0 without crashing."""
        self.assertEqual(len(self.mouse.profiles), 1)
        slot = scratch_slot_for(self.mouse, {})
        self.assertEqual(slot, 0)

    def test_single_profile_software_profile_swapping(self):
        """Ensure AutoPilot can overwrite and use slot 0 on single-profile mice without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_file = os.path.join(tmpdir, "autopilot_profiles.json")
            state_file = os.path.join(tmpdir, "autopilot_state.json")

            with patch("cheddar.autopilot_profiles._STORE_FILE", store_file), \
                 patch("cheddar.autopilot_profiles._STATE_FILE", state_file), \
                 patch("cheddar.autopilot_profiles._STORE_DIR", tmpdir):

                prof = self.mouse.profiles[0]
                prof_data = capture_profile(prof)
                # Modify profile data for specialized work profile
                prof_data["resolutions"][0]["resolution"] = [1200]
                prof_data["leds"][0]["color"] = [0, 255, 255]

                save_store({"Productivity": prof_data})

                # Activate software profile on single-profile mouse
                activate_target(self.mouse, "sw:Productivity", {})

                self.assertEqual(prof.resolutions[0].resolution, (1200,))
                self.assertEqual(prof.leds[0].color, (0, 255, 255))
                self.assertTrue(self.mouse.committed)
                self.assertEqual(autopilot_profiles.active_user_profile(), "Productivity")

    def test_target_label_helpers(self):
        """Test target_label and is_software_target utilities."""
        self.assertTrue(is_software_target("sw:Dota2"))
        self.assertFalse(is_software_target(0))
        self.assertFalse(is_software_target("0"))

        self.assertEqual(target_label("sw:Dota2"), "Dota2")
        self.assertEqual(target_label(0), "0")


# ==============================================================================
# TEST SUITE 5: Profile-switch DPI regression (GUI: profile 1 -> profile 0
# kills the DPI-cycle button until GUI restart)
# ==============================================================================


# TEST SUITE 5: Profile-switch DPI regression (GUI: profile 1 -> profile 0
# kills the DPI-cycle button until GUI restart)
# ==============================================================================


class TestProfileSwitchDpiRegression(unittest.TestCase):
    """Regression tests for: open GUI, activate profile 1, activate profile 0
    (which holds the DPI-cycle button), press the button -> nothing happens;
    after GUI restart it works again.

    Root cause (proven by live ratbagd dumps on a G600): the D-Bus state
    was always correct (profile 0 IsActive, healthy stages, button mapping
    intact) — Profile.SetActive alone never reached the hardware, so the
    mouse stayed on profile 1 where that physical button is a macro.
    Device.Commit() is what flushes the switch to the mouse. A restart
    "fixed" it only because the Rust daemon re-asserts the default
    profile with a commit on startup.
    """

    def _make_profile(self, index, active_res=None, disabled_res=(), is_active=False):
        res_list = [
            MockRatbagdResolution(0, (800,), is_active=(active_res == 0),
                                  is_default=True,
                                  is_disabled=(0 in disabled_res)),
            MockRatbagdResolution(1, (1600,), is_active=(active_res == 1),
                                  is_default=False,
                                  is_disabled=(1 in disabled_res)),
            MockRatbagdResolution(2, (3200,), is_active=(active_res == 2),
                                  is_default=False,
                                  is_disabled=(2 in disabled_res)),
        ]
        btn_list = [
            MockRatbagdButton(0, RatbagdButton.ActionType.BUTTON, 1),
            MockRatbagdButton(1, RatbagdButton.ActionType.BUTTON, 2),
            MockRatbagdButton(2, RatbagdButton.ActionType.BUTTON, 3),
            MockRatbagdButton(
                3,
                RatbagdButton.ActionType.SPECIAL,
                RatbagdButton.ActionSpecial.RESOLUTION_CYCLE_UP,
            ),
        ]
        return MockRatbagdProfile(
            index,
            name=f"Profile {index}",
            is_active=is_active,
            report_rate=1000,
            resolutions=res_list,
            buttons=btn_list,
            leds=[],
        )

    def _make_device(self, profiles):
        return MockRatbagdDevice(
            "dpi_regression_test", "Regression Mouse", "usb:046d:0000:0", profiles
        )

    def _patched_state(self, tmpdir):
        return (
            patch("cheddar.autopilot_profiles._STORE_FILE",
                  os.path.join(tmpdir, "autopilot_profiles.json")),
            patch("cheddar.autopilot_profiles._STATE_FILE",
                  os.path.join(tmpdir, "autopilot_state.json")),
            patch("cheddar.autopilot_profiles._STORE_DIR", tmpdir),
        )

    def test_healthy_switch_commits_to_hardware(self):
        """A switch between healthy profiles must Commit: SetActive alone
        only flips ratbagd's in-memory flag (proven by live G600 dumps —
        IsActive=True while the mouse stayed on the old profile), the
        Commit is what flushes the switch to the hardware."""
        dev = self._make_device(
            [self._make_profile(0, active_res=1, is_active=True),
             self._make_profile(1, active_res=0)]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            patches = self._patched_state(tmpdir)
            for p in patches:
                p.start()
            try:
                activate_target(dev, 1, {})
            finally:
                for p in patches:
                    p.stop()
        self.assertTrue(dev.profiles[1].is_active)
        self.assertFalse(dev.profiles[0].is_active)
        self.assertEqual(dev.active_profile.index, 1)
        self.assertTrue(dev.committed)

    def test_switch_heals_missing_active_resolution(self):
        """If the target profile has no active DPI stage, the switch must
        assert one (and persist it) so the hardware button keeps working."""
        dev = self._make_device(
            [self._make_profile(0, active_res=None, is_active=True),
             self._make_profile(1, active_res=0)]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            patches = self._patched_state(tmpdir)
            for p in patches:
                p.start()
            try:
                activate_target(dev, 0, {})
            finally:
                for p in patches:
                    p.stop()
        prof0 = dev.profiles[0]
        self.assertTrue(prof0.is_active)
        self.assertIsNotNone(prof0.active_resolution)
        self.assertFalse(prof0.active_resolution.is_disabled)
        self.assertTrue(dev.committed)

    def test_switch_heals_disabled_active_resolution(self):
        """If the target's active stage is disabled, fall back to the
        default (enabled) stage instead of leaving the button dead."""
        dev = self._make_device(
            [self._make_profile(0, active_res=1, disabled_res=(1,),
                                is_active=False),
             self._make_profile(1, active_res=0, is_active=True)]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            patches = self._patched_state(tmpdir)
            for p in patches:
                p.start()
            try:
                activate_target(dev, 0, {})
            finally:
                for p in patches:
                    p.stop()
        prof0 = dev.profiles[0]
        self.assertTrue(prof0.is_active)
        # resolution 0 is the default & enabled one -> must take over
        self.assertEqual(prof0.active_resolution.index, 0)
        self.assertTrue(dev.committed)

    def test_rapid_switch_ends_on_usable_stage(self):
        """The exact bug scenario: 1 -> 0 in one session must leave profile
        0 active with a usable DPI stage (no restart needed)."""
        dev = self._make_device(
            [self._make_profile(0, active_res=1, is_active=True),
             self._make_profile(1, active_res=2)]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            patches = self._patched_state(tmpdir)
            for p in patches:
                p.start()
            try:
                activate_target(dev, 1, {})
                activate_target(dev, 0, {})
            finally:
                for p in patches:
                    p.stop()
        self.assertEqual(dev.active_profile.index, 0)
        stage = dev.profiles[0].active_resolution
        self.assertIsNotNone(stage)
        self.assertFalse(stage.is_disabled)

    def test_ensure_valid_noop_when_healthy(self):
        """Healing a healthy profile is a no-op (returns False)."""
        prof = self._make_profile(0, active_res=1)
        self.assertFalse(ensure_valid_active_resolution(prof))
        self.assertEqual(prof.active_resolution.index, 1)

    def test_settled_recommit_fires_when_still_on_target(self):
        """The delayed settled re-commit (the automatic equivalent of the
        manual 'Apply' that unwedges the G600 DPI button) fires when the
        device is still on the expected profile."""
        from cheddar.autopilot_profiles import schedule_settled_recommit

        dev = self._make_device(
            [self._make_profile(0, active_res=1, is_active=True),
             self._make_profile(1, active_res=0)]
        )
        self.assertFalse(dev.committed)
        schedule_settled_recommit(dev, 0, delay=0.05)
        time.sleep(0.4)
        self.assertTrue(dev.committed)

    def test_settled_recommit_skips_after_newer_switch(self):
        """The delayed re-commit must not fire after the user switched to
        another profile meanwhile."""
        from cheddar.autopilot_profiles import schedule_settled_recommit

        dev = self._make_device(
            [self._make_profile(0, active_res=1, is_active=True),
             self._make_profile(1, active_res=0)]
        )
        schedule_settled_recommit(dev, 0, delay=0.05)
        dev.profiles[1].set_active()  # newer switch wins before timer fires
        dev.committed = False  # reset latch to observe the timer alone
        time.sleep(0.4)
        self.assertFalse(dev.committed)


if __name__ == "__main__":
    unittest.main()
