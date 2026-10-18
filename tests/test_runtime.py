from datetime import datetime

from nse_oi_logger.scheduler import generate_market_slots, is_within_market_hours, next_run_time
from nse_oi_logger.store import SQLiteStore


def test_generate_market_slots_count():
    slots = generate_market_slots(start="09:15:00", end="15:15:00", interval_minutes=3)
    assert len(slots) == 121


def test_next_run_time_respects_three_minute_alignment():
    sample = datetime(2026, 10, 18, 9, 18, 17)
    next_slot = next_run_time(sample)
    assert next_slot.strftime("%H:%M:%S") == "09:21:00"


def test_store_deduplicates_same_row(tmp_path):
    db_path = tmp_path / "option_chain.db"
    store = SQLiteStore(db_path)
    row = {
        "symbol": "NIFTY",
        "expiry": "2026-10-28",
        "strike": 24500,
        "time_slot": "09:18:00",
        "underlying_spot": 24500,
        "call_oi": 50,
        "call_change_oi": 5,
        "put_oi": 60,
        "put_change_oi": -3,
        "call_ltp": 100.0,
        "put_ltp": 90.0,
        "call_volume": 10,
        "put_volume": 8,
        "call_iv": 12.0,
        "put_iv": 14.0,
        "pcr": 1.2,
        "net_change_oi": -8,
    }
    inserted_first = store.insert_rows([row])
    inserted_second = store.insert_rows([row])
    assert inserted_first == 1
    assert inserted_second == 0
    assert len(store.fetch_rows_for_strike("NIFTY", "2026-10-28", 24500)) == 1


def test_is_within_market_hours():
    assert is_within_market_hours(datetime(2026, 10, 18, 9, 15, 0)) is True
    assert is_within_market_hours(datetime(2026, 10, 18, 15, 16, 0)) is False
