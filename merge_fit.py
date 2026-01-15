from __future__ import annotations

import argparse

import datetime as dt

from typing import Optional, Union

UTC = dt.timezone.utc
from pathlib import Path
from typing import Dict, Optional

from fit_tool.fit_file import FitFile


# FIT_EPOCH = dt.datetime(1989, 12, 31, tzinfo=dt.timezone.utc)

# def fit_ts_to_dt(ts: int) -> dt.datetime:
#     return FIT_EPOCH + dt.timedelta(seconds=int(ts))

def _as_dt(x: Union[int, float, dt.datetime, None]) -> Optional[dt.datetime]:
    """
    Convert Unix epoch milliseconds → UTC datetime.

    Assumptions (now validated):
      - timestamps are Unix epoch milliseconds
      - datetimes are UTC
    """
    if x is None:
        return None

    if isinstance(x, dt.datetime):
        return x if x.tzinfo else x.replace(tzinfo=UTC)

    # Unix epoch milliseconds
    return dt.datetime.fromtimestamp(int(x) / 1000, tz=UTC)
    
def _field_value_from_fields(msg, field_name: str):
    """Fallback: read a field via msg.fields if attribute isn't present."""
    if msg is None or not hasattr(msg, "fields"):
        return None
    for f in msg.fields:
        if getattr(f, "name", None) == field_name:
            if hasattr(f, "value"):
                return f.value
            if hasattr(f, "raw_value"):
                return f.raw_value
            return None
    return None


def msg_value(msg, field_name: str):
    """
    Preferred: direct attribute access (msg.timestamp, msg.heart_rate, ...).
    Fallback: scan msg.fields.
    """
    if msg is None:
        return None

    # Most typed messages in fit-tool expose decoded fields as attributes
    if hasattr(msg, field_name):
        return getattr(msg, field_name)

    # Fallback for edge cases
    return _field_value_from_fields(msg, field_name)


def extract_polar_hr_series(polar_fit: Path) -> Dict[dt.datetime, int]:
    """
    Extract timestamp -> HR from Polar FIT record messages.
    Uses rec.message.<field> attribute access (per your debug view).
    """
    ff = FitFile.from_file(polar_fit)

    hr_by_time: Dict[dt.datetime, int] = {}
    record_msgs = 0
    record_with_hr = 0

    for rec in ff.records:
        if getattr(rec.header, "is_definition", False):
            continue

        msg = rec.message
        if getattr(msg, "name", None) != "record":
            continue

        record_msgs += 1

        raw_ts = msg_value(msg, "timestamp")  # might be int
        if isinstance(raw_ts, int):
            ts = _as_dt(raw_ts)  # already datetime or convertible
        hr = msg_value(msg, "heart_rate")

        if ts is None or hr is None:
            continue

        record_with_hr += 1
        hr_by_time[ts] = int(hr)

    if not hr_by_time:
        raise RuntimeError(
            "No record-level HR found in Polar FIT.\n"
            "Sanity check: in the debugger, confirm rec.message.name == 'record' "
            "and rec.message.heart_rate is populated for at least some records."
        )

    print(f"[Polar] record messages: {record_msgs}")
    print(f"[Polar] records with HR: {record_with_hr}")
    print(f"[Polar] HR samples extracted: {len(hr_by_time)}")

    return hr_by_time

# --------------------
# CLI
# --------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pm5", type=Path, required=True, help="Concept2/PM5 FIT (primary)")
    ap.add_argument("--polar", type=Path, required=True, help="Polar FIT (HR source)")
    ap.add_argument("--inspect-only", action="store_true", help="Only run PM5 inspection (no HR extraction)")
    args = ap.parse_args()

    if not args.inspect_only:
        _ = extract_polar_hr_series(args.polar)


if __name__ == "__main__":
    main()