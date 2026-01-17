from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fit_tool.fit_file import FitFile


def _summ(v: Any) -> str:
    """Compact printable summary for debugger-style objects."""
    try:
        t = type(v).__name__
    except Exception:
        t = "<?>"
    return f"{v!r} ({t})"


def field_by_name(msg, name: str):
    """Return the Field object (not the value) from msg.fields, or None."""
    if msg is None or not hasattr(msg, "fields"):
        return None
    for f in msg.fields:
        if getattr(f, "name", None) == name:
            return f
    return None


def value_from_msg(msg, name: str):
    """Prefer attribute (msg.timestamp), fallback to msg.fields Field.value."""
    if msg is None:
        return None
    if hasattr(msg, name):
        v = getattr(msg, name)
        # unwrap Field-like attr if needed
        if hasattr(v, "value"):
            return v.value
        return v
    f = field_by_name(msg, name)
    if f is None:
        return None
    return getattr(f, "value", None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pm5", type=Path, required=True)
    args = ap.parse_args()

    ff = FitFile.from_file(args.pm5)

    # Find first non-definition 'record' message
    rec0 = next(
        rec for rec in ff.records
        if (not rec.header.is_definition and rec.message.name == "record")
    )
    msg = rec0.message

    print("PM5 first 'record' message found.")
    print("Message name:", msg.name)

    # Show timestamp raw + type
    ts = value_from_msg(msg, "timestamp")
    print("\n[timestamp]")
    print("timestamp:", _summ(ts))

    # Show common PM5 fields if present
    print("\n[common fields]")
    for k in ("distance", "speed", "enhanced_speed", "power", "cadence", "stroke_rate", "heart_rate"):
        v = value_from_msg(msg, k)
        if v is not None:
            print(f"{k}: {_summ(v)}")

    # Print available field names (helps when Concept2 uses enhanced_* fields)
    print("\n[field names in this record]")
    names = [f.name for f in msg.fields if getattr(f, "name", None)]
    print(names)

    # Mutability test: can we set heart_rate on this message?
    print("\n[mutability test: heart_rate]")
    f_hr = field_by_name(msg, "heart_rate")
    if f_hr is None:
        print("No heart_rate field exists in PM5 record (important!).")
        return

    before = getattr(f_hr, "value", None)
    print("heart_rate before:", _summ(before))

    try:
        f_hr.value = 123
        after = getattr(f_hr, "value", None)
        print("Assigned f_hr.value = 123 successfully.")
        print("heart_rate after:", _summ(after))
    except Exception as e:
        print("FAILED to assign f_hr.value:", repr(e))


if __name__ == "__main__":
    main()
