from __future__ import annotations

from datetime import date


def is_nse_holiday(day: date) -> bool:
    """A small, local holiday guard for the app. Replace with an NSE holiday feed when expanded."""
    weekend = day.weekday() >= 5
    if weekend:
        return True
    # A few common holidays; extend as needed.
    fixed_holidays = {
        (1, 1),
        (8, 15),
        (10, 2),
        (11, 1),
        (12, 25),
    }
    return (day.month, day.day) in fixed_holidays
