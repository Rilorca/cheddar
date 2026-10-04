#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Debug helper: dump live ratbagd state (profiles, DPI stages, buttons).

Usage (with the bug active and the GUI still open):
    python3 tools/dump-ratbag-state.py > /tmp/roto.txt 2>&1
Then paste /tmp/roto.txt in the bug report.
"""
import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)


def proxy(path, iface):
    return Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.NONE,
        None,
        "org.freedesktop.ratbag1",
        path,
        iface,
        None,
    )


def prop(px, name):
    try:
        v = px.get_cached_property(name)
        return v.unpack() if v is not None else None
    except Exception as e:
        return f"<error {e}>"


mgr = proxy("/org/freedesktop/ratbag1", "org.freedesktop.ratbag1.Manager")
print("APIVersion:", prop(mgr, "APIVersion"))
for dev in prop(mgr, "Devices") or []:
    dp = proxy(dev, "org.freedesktop.ratbag1.Device")
    print("== device", dev, "| Name:", prop(dp, "Name"))
    for p in prop(dp, "Profiles") or []:
        pp = proxy(p, "org.freedesktop.ratbag1.Profile")
        print(
            f"  profile Index={prop(pp, 'Index')}"
            f" IsActive={prop(pp, 'IsActive')}"
            f" IsDirty={prop(pp, 'IsDirty')}"
            f" Disabled={prop(pp, 'Disabled')}"
            f" ReportRate={prop(pp, 'ReportRate')}"
        )
        for r in prop(pp, "Resolutions") or []:
            rp = proxy(r, "org.freedesktop.ratbag1.Resolution")
            print(
                f"    res idx={prop(rp, 'Index')} dpi={prop(rp, 'Resolution')}"
                f" active={prop(rp, 'IsActive')}"
                f" default={prop(rp, 'IsDefault')}"
                f" disabled={prop(rp, 'IsDisabled')}"
            )
        for b in prop(pp, "Buttons") or []:
            bp = proxy(b, "org.freedesktop.ratbag1.Button")
            print(f"    btn idx={prop(bp, 'Index')} mapping={prop(bp, 'Mapping')}")

print()
print("== G600 hardware ground truth (hidraw feature report 0xF0) ==")
print("(what the MOUSE itself reports, independent of ratbagd)")
try:
    import array
    import fcntl
    import glob
    import os

    HIDIOCGFEATURE_4 = 0xC0044807
    found = False
    for path in sorted(glob.glob("/dev/hidraw*")):
        try:
            fd = os.open(path, os.O_RDWR)
        except OSError as e:
            print(f"  {path}: cannot open ({e.strerror})")
            continue
        try:
            buf = array.array("B", [0xF0, 0, 0, 0])
            fcntl.ioctl(fd, HIDIOCGFEATURE_4, buf, True)
            if buf[0] == 0xF0:
                prof_idx = (buf[1] >> 4) & 0x0F
                res_idx = (buf[1] >> 1) & 0x03
                print(
                    f"  {path}: raw=0x{buf[1]:02x}"
                    f" -> HW profile slot={prof_idx}, HW dpi stage={res_idx}"
                )
                found = True
            else:
                print(f"  {path}: no 0xF0 report (got 0x{buf[0]:02x})")
        except OSError as e:
            print(f"  {path}: ioctl failed ({e.strerror})")
        finally:
            os.close(fd)
    if not found:
        print("  (no hidraw device answered the G600 0xF0 report)")
except Exception as e:
    print(f"  hw read failed: {e}")
