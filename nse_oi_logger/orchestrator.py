from __future__ import annotations

from datetime import datetime
from pathlib import Path

from nse_oi_logger.excel_writer import write_daily_workbook
from nse_oi_logger.fetcher import NseFetcher
from nse_oi_logger.holidays import is_nse_holiday
from nse_oi_logger.parser import compute_auto_atm_strikes, extract_strike_rows
from nse_oi_logger.scheduler import is_weekday, is_within_market_hours
from nse_oi_logger.store import SQLiteStore


class OptionChainLogger:
    def __init__(self, symbol: str, expiry: str | None, strikes: list[int], db_path: str | Path, output_dir: str | Path, auto_atm: bool = False, atm_window: int = 2):
        self.symbol = symbol.upper()
        self.expiry = expiry
        self.strikes = list(strikes)
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.auto_atm = auto_atm
        self.atm_window = atm_window
        self.store = SQLiteStore(self.db_path)

    def _resolve_expiry(self, payload: dict) -> str:
        if self.expiry:
            return self.expiry
        expiry_dates = payload.get("records", {}).get("expiryDates") or []
        if expiry_dates:
            return str(expiry_dates[0])
        return "nearest"

    def _resolve_strikes(self, payload: dict) -> list[int]:
        selected = list(self.strikes)
        if not self.auto_atm:
            return selected

        raw_underlying = payload.get("records", {}).get("underlyingValue")
        if raw_underlying is None:
            return selected

        atm_strikes = compute_auto_atm_strikes(float(raw_underlying), step=100, window=self.atm_window)
        selected.extend(atm_strikes)
        return sorted(set(selected))

    def _market_window_allowed(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        if not is_weekday(now):
            return False
        if is_nse_holiday(now.date()):
            return False
        return is_within_market_hours(now, start="09:15:00", end="15:15:00")

    def process_cycle(self) -> str:
        now = datetime.now()
        if not self._market_window_allowed(now):
            return f"Skipped cycle outside market hours for {self.symbol} at {now:%Y-%m-%d %H:%M:%S}"

        fetcher = NseFetcher()
        payload = fetcher.fetch_chain(self.symbol, self.expiry)
        expiry_value = self._resolve_expiry(payload)
        selected = self._resolve_strikes(payload)
        rows = extract_strike_rows(payload, self.symbol, expiry_value, now, set(selected))

        if not rows:
            return f"No option rows found for {self.symbol} and expiry {expiry_value} at {now:%H:%M:%S}"

        inserted = self.store.insert_rows(rows)
        persisted_rows = self.store.fetch_rows_for_symbol(self.symbol, expiry_value, selected)
        workbook_path = write_daily_workbook(
            self.output_dir,
            self.symbol,
            {strike: persisted_rows.get(strike, []) for strike in selected},
            trade_date=now,
        )
        return (
            f"Processed {self.symbol} {expiry_value} at {now:%H:%M:%S}; "
            f"inserted={inserted}; workbook={workbook_path}"
        )
