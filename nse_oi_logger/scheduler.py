from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def generate_market_slots(start: str = "09:15:00", end: str = "15:15:00", interval_minutes: int = 3) -> list[datetime]:
    start_dt = datetime.strptime(start, "%H:%M:%S").time()
    end_dt = datetime.strptime(end, "%H:%M:%S").time()
    base_day = datetime(2000, 1, 1)
    slots: list[datetime] = []
    current = datetime.combine(base_day.date(), start_dt)
    end_time = datetime.combine(base_day.date(), end_dt)
    while current <= end_time:
        slots.append(current)
        current += timedelta(minutes=interval_minutes)
    return slots


def is_weekday(date_value: datetime) -> bool:
    return date_value.weekday() < 5


def is_within_market_hours(slot_time: datetime, start: str = "09:15:00", end: str = "15:15:00") -> bool:
    start_dt = datetime.strptime(start, "%H:%M:%S").time()
    end_dt = datetime.strptime(end, "%H:%M:%S").time()
    current_time = slot_time.time()
    return start_dt <= current_time <= end_dt


def next_run_time(now: datetime | None = None) -> datetime:
    if now is None:
        now = datetime.now(IST)

    candidate = now.replace(second=0, microsecond=0)
    if now.second > 0 or now.microsecond > 0:
        candidate += timedelta(minutes=1)

    if candidate.minute % 3 != 0:
        remainder = candidate.minute % 3
        candidate += timedelta(minutes=3 - remainder)

    if candidate <= now:
        candidate += timedelta(minutes=3)

    return candidate
