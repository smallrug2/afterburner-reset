"""afterburner_reset.py - Rewrite an MSI Afterburner profile .cfg with safe values.

Purpose: restore a stock profile plus one conservative OC profile
    (small core bump, memory at stock, stock voltage curve reused from
    the file's [Defaults] section). The original file is backed up to
    .bak before writing. Voltage is never modified.

Usage:
    python afterburner_reset.py --profile "C:\\path\\to\\profile.cfg"
    python afterburner_reset.py --profile profile.cfg --core-mhz 50 --mem-mhz 0

Platform: Windows-only (MSI Afterburner profiles live on Windows).
    Exits with a message on other OSes. No third-party dependencies.
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path


def extract_stock_vf(text):
    """Pull the untouched stock V/F curve out of the [Defaults] section."""
    m = re.search(r"\[Defaults\]\s*\r?\nFormat=2\r?\nCoreClkBoost=0\r?\n"
                  r"VFCurve=([0-9A-Fa-f]+)\r?\n", text)
    if not m:
        # Fall back to whatever VFCurve appears first.
        m2 = re.search(r"VFCurve=([0-9A-Fa-f]+)", text)
        if not m2:
            raise ValueError("no VFCurve found in profile; refusing to write")
        return m2.group(1)
    return m.group(1)


def block(name, core, mem, vf):
    return ("[%s]\nFormat=2\nCoreClkBoost=%d\nVFCurve=%s\nMemClkBoost=%d\n"
            % (name, core, vf, mem))


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Reset MSI Afterburner profile to stock + safe OC")
    p.add_argument("--profile", required=True,
                   help="Path to the Afterburner .cfg profile")
    p.add_argument("--core-mhz", type=int, default=50,
                   help="Safe-OC core offset in MHz (0 = stock)")
    p.add_argument("--mem-mhz", type=int, default=0,
                   help="Safe-OC memory offset in MHz (0 = stock)")
    return p.parse_args(argv)


def main(argv=None):
    if os.name != "nt":
        print("afterburner_reset is Windows-only (MSI Afterburner profiles "
              "exist on Windows). Nothing was changed.", file=sys.stderr)
        sys.exit(1)
    args = parse_args(argv)
    profile = Path(args.profile)
    if not profile.is_file():
        print("ERROR: profile not found: %s" % profile, file=sys.stderr)
        sys.exit(2)
    if args.core_mhz < 0 or args.mem_mhz < 0:
        print("ERROR: --core-mhz/--mem-mhz must be >= 0", file=sys.stderr)
        sys.exit(2)
    # Offsets in the cfg are in kHz (50 MHz -> 50000).
    coreRaw, memRaw = args.core_mhz * 1000, args.mem_mhz * 1000
    text = profile.read_text(encoding="utf-8", errors="replace")
    stock_vf = extract_stock_vf(text)
    print("stock VF curve length:", len(stock_vf))
    new = ("[Startup]\nFormat=2\nCoreClkBoost=0\nVFCurve=\nMemClkBoost=0\n"
           + block("Profile1", 0, 0, stock_vf)
           + "[Settings]\nCaptureDefaults=0\n"
           + block("Profile2", coreRaw, memRaw, stock_vf))
    backup = profile.with_suffix(profile.suffix + ".bak")
    shutil.copyfile(profile, backup)
    print("backed up original to", backup)
    profile.write_text(new, encoding="utf-8", newline="")
    print("wrote %s (Profile1=stock, Profile2=+%dMHz core/+%dMHz mem, "
          "voltage untouched)" % (profile, args.core_mhz, args.mem_mhz))


if __name__ == "__main__":
    main()
