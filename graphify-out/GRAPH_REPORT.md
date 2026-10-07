# Graph Report - piper-autopilot  (2026-10-07)

## Corpus Check
- 163 files · ~252,703 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1131 nodes · 2159 edges · 74 communities (61 shown, 13 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 104 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Mouse Map SVG & Leaders
- Process Watcher & Daemon Core
- System Tray & Notifications
- AutoPilot Config & Rules
- Mouse Map SVG & Leaders
- AutoPilot Config & Rules
- LED Lighting & Dialog
- Ratbagd D-Bus Client
- AutoPilot Config & Rules
- Ratbagd D-Bus Client
- Profile Storage & Activation
- LED Lighting & Dialog
- AutoPilot Config & Rules
- Profile Storage & Activation
- Mouse Map SVG & Leaders
- AutoPilot Config & Rules
- Ratbagd D-Bus Client
- Mouse Map SVG & Leaders
- LED Lighting & Dialog
- AutoPilot Config & Rules
- AutoPilot Config & Rules
- LED Lighting & Dialog
- LED Lighting & Dialog
- LED Lighting & Dialog
- Button Mapping & Actions
- LED Lighting & Dialog
- LED Lighting & Dialog
- LED Lighting & Dialog
- LED Lighting & Dialog
- LED Lighting & Dialog
- Process Watcher & Daemon Core
- Button Mapping & Actions
- LED Lighting & Dialog
- System Tray & Notifications
- AutoPilot Config & Rules
- System Tray & Notifications
- LED Lighting & Dialog
- LED Lighting & Dialog
- Mouse Map SVG & Leaders
- Ratbagd D-Bus Client
- Ratbagd D-Bus Client
- LED Lighting & Dialog
- AutoPilot Config & Rules
- AutoPilot Config & Rules
- Ratbagd D-Bus Client
- Button Mapping & Actions
- AutoPilot Config & Rules
- AutoPilot Config & Rules
- Ratbagd D-Bus Client
- AutoPilot Config & Rules
- Button Mapping & Actions
- Mouse Map SVG & Leaders
- LED Lighting & Dialog
- AutoPilot Config & Rules
- AutoPilot Config & Rules
- Ratbagd D-Bus Client
- DPI & Resolution Settings
- HashMap HashSet Option
- DPI & Resolution Settings
- AutoPilot Config & Rules
- name The name of the profile Set the nam
- check-files-in-git.sh GIT_DIR check-file
- meson_install.sh meson_install.sh script
- python-black-check.sh python-black-check
- python-ruff-check.sh python-ruff-check.s
- build-rust-daemon.sh build-rust-daemon.s
- python-black.sh python-black.sh script
- python-ruff.sh python-ruff.sh script
- cheddar-autopilot

## God Nodes (most connected - your core abstractions)
1. `RatbagdDevice` - 63 edges
2. `RatbagdProfile` - 62 edges
3. `MousePerspective` - 45 edges
4. `RatbagdButton` - 45 edges
5. `AutoPilotPage` - 39 edges
6. `MouseMap` - 34 edges
7. `Window` - 33 edges
8. `Ratbagd` - 31 edges
9. `ButtonDialog` - 30 edges
10. `RatbagdLed` - 28 edges

## Surprising Connections (you probably didn't know these)
- `TestFaugusIntegration` --uses--> `AutoPilotWatcher`  [INFERRED]
  tests/test_stability.py → cheddar/autopilot_watcher.py
- `MockRatbagdDevice` --uses--> `RatbagDeviceType`  [INFERRED]
  tests/test_devices_and_features.py → cheddar/ratbagd.py
- `TestLiveLogitechG600` --uses--> `RatbagDeviceType`  [INFERRED]
  tests/test_devices_and_features.py → cheddar/ratbagd.py
- `TestLiveLogitechG600` --uses--> `Ratbagd`  [INFERRED]
  tests/test_devices_and_features.py → cheddar/ratbagd.py
- `TestFaugusIntegration` --uses--> `Ratbagd`  [INFERRED]
  tests/test_stability.py → cheddar/ratbagd.py

## Import Cycles
- None detected.

## Communities (74 total, 13 thin omitted)

### Community 0 - "Mouse Map SVG & Leaders"
Cohesion: 0.07
Nodes (20): MouseMap, _MouseMapChild, Any, Context, Widget, Adds the given widget to the map, bound to the given SVG element identifier. If…, Removes the given widget from the map. @param widget The widget to remove, as…, Invokes the given callback on each child, with the given parameters. @param… (+12 more)

### Community 1 - "Process Watcher & Daemon Core"
Cohesion: 0.07
Nodes (22): AutoPilotDaemon, main(), The rules to act on: none while the user has AutoPilot disabled. The GUI toggle…, _add_name(), AutoPilotWatcher, _basename_any_os(), _focused_pid(), is_flatpak() (+14 more)

### Community 2 - "System Tray & Notifications"
Cohesion: 0.09
Nodes (23): Category, CheddarTray, is_light_theme(), launch_cheddar_gui(), Box, Default, Error, Option (+15 more)

### Community 3 - "AutoPilot Config & Rules"
Cohesion: 0.09
Nodes (18): Button, Callback, Scale, ScrollType, Template, Widget, A Gtk.ListBoxRow subclass containing the widgets to configure a resolution., ResolutionRow (+10 more)

### Community 4 - "Mouse Map SVG & Leaders"
Cohesion: 0.08
Nodes (19): DeviceRow, Template, A Gtk.ListBoxRow subclass to present devices in the welcome perspective., get_svg(), Callback, ListBox, ListBoxRow, Property (+11 more)

### Community 5 - "AutoPilot Config & Rules"
Cohesion: 0.08
Nodes (19): LedDialog, Callback, Property, Scale, ScrollType, Template, A Gtk.Dialog subclass to implement the dialog that shows the configuration…, Instantiates a new LedDialog. @param ratbagd_led The LED to configure, as… (+11 more)

### Community 6 - "LED Lighting & Dialog"
Cohesion: 0.07
Nodes (16): ProfileRow, Button, Callback, Property, Template, A Gtk.ListBoxRow subclass containing the widgets to display a profile in the…, Activates the profile paired with this row., GObject (+8 more)

### Community 7 - "Ratbagd D-Bus Client"
Cohesion: 0.13
Nodes (9): Ratbagd, The ratbagd top-level object. Provides a list of devices available through…, Returns the requested device, or None., Event, Template, Widget, A Gtk.ApplicationWindow subclass to implement the main application window. This…, Instantiates a new Window. @param ratbag The ratbag instance to connect to, as… (+1 more)

### Community 8 - "AutoPilot Config & Rules"
Cohesion: 0.09
Nodes (11): ApplicationCommandLine, Application, Called on primary instance for every invocation., Called on launch or when user activates application from launcher., Called by GUI when rules or default profile are modified., Completely exit the application., A Gtk.Application subclass handling lifecycle, background AutoPilot watcher,…, Instantiates a new Application. (+3 more)

### Community 9 - "Ratbagd D-Bus Client"
Cohesion: 0.10
Nodes (23): RatbagCapabilityError, RatbagdDBusTimeoutError, RatbagDeviceError, RatbagdIncompatibleError, RatbagdUnavailableError, RatbagError, RatbagImplementationError, RatbagSystemError (+15 more)

### Community 10 - "Profile Storage & Activation"
Cohesion: 0.09
Nodes (12): AutoPilotPage, Button, Context, The AutoPilot tab shown inside Cheddar's per-device stack-switcher. Integrates…, Add a separator between rows (Cheddar style)., The onboard slot AutoPilot reserves for named profiles., Invoke callback whenever the AutoPilot toggle changes., Name of the user profile currently on the scratch slot, if any — used by the… (+4 more)

### Community 11 - "LED Lighting & Dialog"
Cohesion: 0.09
Nodes (19): setter, An integer of the current button mapping, if mapping to a button or None…, Set the button mapping to the given button. @param button The button to map to,…, A RatbagdMacro object representing the currently set macro or None otherwise., Set the macro to the macro represented by the given RatbagdMacro object. @param…, An enum describing the current special mapping, if mapped to special or None…, Set the button mapping to the given special entry. @param special The special…, The LED's effect duration in ms, values range from 0 to 10000. (+11 more)

### Community 12 - "AutoPilot Config & Rules"
Cohesion: 0.11
Nodes (18): AutoPilotConfig, config_path(), load_config(), Default, Error, HashMap, Option, Result (+10 more)

### Community 13 - "Profile Storage & Activation"
Cohesion: 0.14
Nodes (20): activate_target(), active_user_profile(), ensure_valid_active_resolution(), is_software_target(), load_store(), Make sure the profile has exactly one usable active DPI stage. After a profile…, Re-commit a profile switch once the mouse has settled. Proven by live G600…, Human-readable name of a rule target (software profile name as-is; onboard… (+12 more)

### Community 14 - "Mouse Map SVG & Leaders"
Cohesion: 0.10
Nodes (14): Property, Instantiates a new MouseMap. @param layer The SVG layer whose leaders to draw,…, RatbagdDevice, Represents a ratbagd device., Re-read the live active-profile/resolution state from ratbagd into the local…, Remove a device from the list. @param device The device to remove, as…, Unit tests for Faugus launcher game detection and AutoPilot profile switching., Test that Window auto-reconnects when ratbagd disconnects. (+6 more)

### Community 15 - "AutoPilot Config & Rules"
Cohesion: 0.14
Nodes (5): MousePerspective, Template, Release resources held by this perspective. Called by Window when the…, The perspective to configure a mouse., Stack

### Community 16 - "Ratbagd D-Bus Client"
Cohesion: 0.09
Nodes (6): _RatbagdDBus, An array of possible values for ActionType., The unique identifier for this device model., The firmware version of the device., The capabilities of this profile as an array. Capabilities not present on the…, The list of supported report rates

### Community 17 - "Mouse Map SVG & Leaders"
Cohesion: 0.15
Nodes (12): # TODO: think how we should handle this., # FIXME: why is this needed if this child's type is `titlebar` already?, # TODO: remove this when we're out of the transition to toned down SVGs, # TODO: account for children sticking out under or above the SVG, if, # TODO: get rid of this duplicated logic., # TODO: preserve the active tab., # NOTE: Device.Commit() after SetActive is mandatory, not, # TODO: display this in the app (+4 more)

### Community 18 - "LED Lighting & Dialog"
Cohesion: 0.16
Nodes (21): _find_game_exe(), _find_proton_shortcut_icon(), Game, _generate_hints(), _heroic_json(), installed_games(), _normalize(), Lowercase alphanumerics only, for fuzzy name comparison. (+13 more)

### Community 19 - "AutoPilot Config & Rules"
Cohesion: 0.13
Nodes (9): ButtonDialog, Button, Callback, Event, ListBox, ListBoxRow, RadioButton, Grabs the keyboard seat. Returns True on success, False on failure. Gratefully… (+1 more)

### Community 20 - "AutoPilot Config & Rules"
Cohesion: 0.15
Nodes (11): ensure_daemon_service_running(), is_daemon_service_enabled(), Ensure the native Rust daemon service is started and active., Check if the native Rust daemon is enabled to start on login., Start the user systemd service., Stop the user systemd service., start_daemon_service(), stop_daemon_service() (+3 more)

### Community 21 - "LED Lighting & Dialog"
Cohesion: 0.10
Nodes (10): Property, The index of this button., An enum describing the action type of the button. One of ActionType.NONE,…, A list of RatbagdDevice objects supported by ratbagd., The device name, usually provided by the kernel., The device type, see RatbagDeviceType, A list of RatbagdProfile objects provided by this device., The currently active profile. This is a non-DBus property computed over the… (+2 more)

### Community 22 - "LED Lighting & Dialog"
Cohesion: 0.10
Nodes (11): RatbagdResolution, Represents a ratbagd resolution., The capabilities of this resolution as an array. Capabilities not present on…, The index of this resolution., Convert resolution from what D-Bus API returns - either an int or a tuple of…, The list of supported DPI values, True if this is the currently active resolution, False otherwise, True if this is the currently default resolution, False otherwise (+3 more)

### Community 23 - "LED Lighting & Dialog"
Cohesion: 0.15
Nodes (9): AdvancedPage, Button, Callback, RadioButton, Switch, Template, Advanced settings stack., Instantiates a new AdvancedPage. (+1 more)

### Community 24 - "Button Mapping & Actions"
Cohesion: 0.12
Nodes (12): ErrorPerspective, Property, Template, Widget, A perspective to present an error condition in a user-friendly manner., Instantiates a new ErrorPerspective. @param message The error message to…, The name of this perspective., The titlebar to this perspective. (+4 more)

### Community 25 - "LED Lighting & Dialog"
Cohesion: 0.30
Nodes (7): RatbagClient, Connection, Result, Self, String, Vec, OwnedObjectPath

### Community 26 - "LED Lighting & Dialog"
Cohesion: 0.19
Nodes (3): MockRatbagdProfile, Property, Simulated RatbagdProfile object for unit testing.

### Community 27 - "LED Lighting & Dialog"
Cohesion: 0.20
Nodes (9): If the target's active stage is disabled, fall back to the default (enabled)…, The exact bug scenario: 1 -> 0 in one session must leave profile 0 active with…, Healing a healthy profile is a no-op (returns False)., The delayed settled re-commit (the automatic equivalent of the manual 'Apply'…, The delayed re-commit must not fire after the user switched to another profile…, Regression tests for: open GUI, activate profile 1, activate profile 0 (which…, A switch between healthy profiles must Commit: SetActive alone only flips…, If the target profile has no active DPI stage, the switch must assert one (and… (+1 more)

### Community 28 - "LED Lighting & Dialog"
Cohesion: 0.11
Nodes (11): RatbagdLed, Represents a ratbagd led., The index of this led., This led's mode, one of Mode.OFF, Mode.ON, Mode.CYCLE and Mode.BREATHING., Set the led's mode to the given mode. @param mode The new mode, as one of…, The supported modes as a list, An integer triple of the current LED color., Set the led color to the given color. @param color An RGB color, as an integer… (+3 more)

### Community 29 - "LED Lighting & Dialog"
Cohesion: 0.12
Nodes (10): RatbagdMacro, Represents a button macro. Note that it uses keycodes as defined by…, A list of (RatbagdButton.Macro.*, value) tuples representing the current macro., Instantiates a new RatbagdMacro instance from the given macro in libratbag…, Applies the currently cached macro., Appends the given event to the current macro. @param type The type of event, as…, Tests every feature and function against a simulated Logitech G Pro Wireless., Test enabling and mapping previously disabled side buttons on G Pro Wireless. (+2 more)

### Community 30 - "Process Watcher & Daemon Core"
Cohesion: 0.19
Nodes (15): main(), Box, Error, Result, add_name(), basename_any_os(), focused_pid(), is_flatpak() (+7 more)

### Community 31 - "Button Mapping & Actions"
Cohesion: 0.12
Nodes (8): Property, Widget, A row in the profile switcher for a user-created (AutoPilot) profile. Marked…, Instantiates a new MousePerspective., The name of this perspective., The titlebar to this perspective., Whether this perspective wants a back button to be displayed in case there is…, UserProfileRow

### Community 32 - "LED Lighting & Dialog"
Cohesion: 0.15
Nodes (3): MockRatbagdButton, setter, Simulated RatbagdButton object for unit testing.

### Community 33 - "System Tray & Notifications"
Cohesion: 0.17
Nodes (6): CheckMenuItem, Locate the directory containing the cheddar-tray.png icon., Refresh the tray menu items to match current app state., System tray / status icon integration for Cheddar. Uses AyatanaAppIndicator3 /…, TrayIcon, Menu

### Community 34 - "AutoPilot Config & Rules"
Cohesion: 0.19
Nodes (11): load(), Any, save(), _load_game_icon(), _profile_label(), ListBoxRow, Load a game icon as a rounded squircle of `size` px; themed fallback., Clip a pixbuf to a squircle with rounded corners (Libadwaita style). (+3 more)

### Community 35 - "System Tray & Notifications"
Cohesion: 0.22
Nodes (8): Arc, Notifier, Connection, Option, Self, Mutex, Tray, Value

### Community 36 - "LED Lighting & Dialog"
Cohesion: 0.20
Nodes (5): is_daemon_service_active(), Check if the native Rust daemon is currently running via systemd., Switch, Write a saved profile onto the mouse and activate it, so the user can use it or…, Display name for a rule target: onboard profile name, or the software profile's…

### Community 37 - "LED Lighting & Dialog"
Cohesion: 0.17
Nodes (6): Widget, The chosen rule target: onboard profile index (int) or a software profile…, Prompt for a name and save the mouse's current setup under it. Returns the…, Modal dialog to add or edit a single game→profile rule., _RuleDialog, ComboBoxText

### Community 38 - "Mouse Map SVG & Leaders"
Cohesion: 0.23
Nodes (9): check_buttons(), check_elements(), check_layers(), check_leds(), check_size(), check_svg(), Check there are layers (well, groups) for the components we require., Checks for elements of the form 'prefixN' in the root tag. Any elements found… (+1 more)

### Community 39 - "Ratbagd D-Bus Client"
Cohesion: 0.20
Nodes (9): Instantiates a new ButtonRow. @param description The text to display in the…, The action type as last set in the dialog, one of RatbagdButton.ActionType.*., ActionSpecial, ActionType, ColorDepth, Macro, Mode, RatbagErrorCode (+1 more)

### Community 42 - "AutoPilot Config & Rules"
Cohesion: 0.27
Nodes (4): Instantiates a new ButtonDialog. @param ratbagd_button The button to configure,…, RatbagdButton, Disables this button., Represents a ratbagd button.

### Community 43 - "AutoPilot Config & Rules"
Cohesion: 0.22
Nodes (5): ButtonsPage, Button, ResponseType, The second stack page, exposing the button configuration., Instantiates a new ButtonsPage. @param ratbag_device The ratbag device to…

### Community 44 - "Ratbagd D-Bus Client"
Cohesion: 0.40
Nodes (8): friendly_key(), _friendly_name(), humanize_macro(), Human label for a RatbagdMacro. Collapses press+release into a tap, recognizes…, Human label for a single evdev keycode., _short_mod(), _strip(), evcode_to_str()

### Community 45 - "Button Mapping & Actions"
Cohesion: 0.24
Nodes (4): Button, Callback, ListBox, ListBoxRow

### Community 46 - "AutoPilot Config & Rules"
Cohesion: 0.20
Nodes (5): Comprehensive tests on the user's physical Logitech G600 mouse. Verifies every…, Test reading G600 top-level attributes: id, name, model, type, profiles count., Test reading G600 profile properties, resolution, report rate, buttons, LEDs., Test that capture_profile correctly captures full G600 profile configuration., TestLiveLogitechG600

### Community 47 - "AutoPilot Config & Rules"
Cohesion: 0.44
Nodes (8): _get_autostart_dir(), _get_autostart_path(), _get_legacy_path(), is_autostart_enabled(), is_flatpak(), Check whether Cheddar is configured to launch on desktop startup., Enable or disable Cheddar launching on desktop login., set_autostart_enabled()

### Community 48 - "Ratbagd D-Bus Client"
Cohesion: 0.22
Nodes (4): Commits all changes made to the device. This is implemented asynchronously…, Set this profile to be the active profile., Set this resolution to be the active one., Set this resolution to be the default.

### Community 49 - "AutoPilot Config & Rules"
Cohesion: 0.22
Nodes (5): Tests every feature and function against a simulated Logitech G502 Hero., Test setting active profile and signal emission on G502., Test setting and getting separate XY resolution on G502., Test controlling both primary and indicator LEDs on G502., TestSimulatedLogitechG502Hero

### Community 50 - "Button Mapping & Actions"
Cohesion: 0.25
Nodes (5): ButtonRow, Property, Template, A Gtk.ListBoxRow subclass to implement the rows that show up in the…, The mapping as last set in the dialog. Note that the type depends on…

### Community 53 - "AutoPilot Config & Rules"
Cohesion: 0.33
Nodes (6): apply_profile(), capture_profile(), Any, Write a captured configuration into an onboard profile slot. Only touches…, Serialize an onboard profile's full configuration., Test capturing a profile with separate XY resolution and applying to scratch…

### Community 54 - "AutoPilot Config & Rules"
Cohesion: 0.33
Nodes (4): The onboard slot software profiles get written into. Defaults to the last slot;…, scratch_slot_for(), Test scratch slot resolution for G600 under various user configurations., Ensure single-profile mouse resolves scratch slot cleanly to slot 0 without…

### Community 55 - "Ratbagd D-Bus Client"
Cohesion: 0.33
Nodes (5): # HACK: we don't want to use SysRq as a keybinding, but we do want, # TODO: this needs to be checked for its Wayland support., # TODO: display this somewhere in the UI instead., RatbagDeviceType, DeviceType property specified in the .device files

### Community 56 - "DPI & Resolution Settings"
Cohesion: 0.60
Nodes (3): extract_u32(), read_g600_hw_slot(), Option

### Community 57 - "HashMap HashSet Option"
Cohesion: 0.40
Nodes (5): HashMap, HashSet, Option, String, WatcherState

### Community 59 - "DPI & Resolution Settings"
Cohesion: 0.50
Nodes (3): _DPIEntry, A subclass of Gtk.Entry with an overridden method for input validation. This…, Overrides the default Gtk.Editable insert-text handler to validate numerical…

### Community 60 - "AutoPilot Config & Rules"
Cohesion: 0.50
Nodes (3): Unit tests for XDG autostart configuration., Test enabling and disabling autostart file generation., TestAutostart

## Knowledge Gaps
- **9 isolated node(s):** `cheddar-autopilot`, `meson_install.sh script`, `check-files-in-git.sh script`, `GIT_DIR`, `python-black-check.sh script` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RatbagdDevice` connect `Mouse Map SVG & Leaders` to `Mouse Map SVG & Leaders`, `AutoPilot Config & Rules`, `AutoPilot Config & Rules`, `Mouse Map SVG & Leaders`, `AutoPilot Config & Rules`, `Ratbagd D-Bus Client`, `Ratbagd D-Bus Client`, `Profile Storage & Activation`, `AutoPilot Config & Rules`, `Profile Storage & Activation`, `AutoPilot Config & Rules`, `Ratbagd D-Bus Client`, `Mouse Map SVG & Leaders`, `Ratbagd D-Bus Client`, `LED Lighting & Dialog`, `AutoPilot Config & Rules`, `LED Lighting & Dialog`, `Button Mapping & Actions`?**
  _High betweenness centrality (0.168) - this node is a cross-community bridge._
- **Why does `RatbagdProfile` connect `LED Lighting & Dialog` to `AutoPilot Config & Rules`, `AutoPilot Config & Rules`, `LED Lighting & Dialog`, `AutoPilot Config & Rules`, `Ratbagd D-Bus Client`, `AutoPilot Config & Rules`, `LED Lighting & Dialog`, `Profile Storage & Activation`, `Mouse Map SVG & Leaders`, `AutoPilot Config & Rules`, `Ratbagd D-Bus Client`, `Mouse Map SVG & Leaders`, `Ratbagd D-Bus Client`, `AutoPilot Config & Rules`, `LED Lighting & Dialog`, `LED Lighting & Dialog`, `LED Lighting & Dialog`, `name The name of the profile Set the nam`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Why does `AutoPilotPage` connect `Profile Storage & Activation` to `Process Watcher & Daemon Core`, `AutoPilot Config & Rules`, `LED Lighting & Dialog`, `LED Lighting & Dialog`, `Mouse Map SVG & Leaders`, `AutoPilot Config & Rules`, `Mouse Map SVG & Leaders`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `RatbagdDevice` (e.g. with `AdvancedPage` and `activate_target()`) actually correct?**
  _`RatbagdDevice` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `RatbagdProfile` (e.g. with `AdvancedPage` and `apply_profile()`) actually correct?**
  _`RatbagdProfile` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `MousePerspective` (e.g. with `AdvancedPage` and `AutoPilotPage`) actually correct?**
  _`MousePerspective` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `RatbagdButton` (e.g. with `apply_profile()` and `capture_profile()`) actually correct?**
  _`RatbagdButton` has 13 INFERRED edges - model-reasoned connections that need verification._