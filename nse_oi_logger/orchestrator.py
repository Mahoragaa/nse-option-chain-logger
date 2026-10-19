from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from nse_oi_logger.excel_writer import write_daily_workbook
from nse_oi_logger.fetcher import NseFetcher
from nse_oi_logger.holidays import is_nse_holiday
from nse_oi_logger.parser import compute_auto_atm_strikes, extract_strike_rows
from nse_oi_logger.scheduler import is_weekday, is_within_market_hours
from nse_oi_logger.store import SQLiteStore


class OptionChainLogger:
    def __init__(
        self,
        symbol: str,
        expiry: str | None,
        strikes: list[int],
        db_path: str | Path,
        output_dir: str | Path,
        auto_atm: bool = False,
        atm_window: int = 2,
        workbook_publisher: Callable[
            [str, dict[int | tuple[int, str], list[dict]], datetime], str
        ]
        | None = None,
        strike_expiries: dict[int, list[str]] | None = None,
    ):
        self.symbol = symbol.upper()
        self.expiry = expiry
        self.strikes = list(strikes)
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.auto_atm = auto_atm
        self.atm_window = atm_window
        self.workbook_publisher = workbook_publisher
        self.strike_expiries = strike_expiries
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
        rows: list[dict] = []
        selected_pairs: list[tuple[int, str]] = []
        if self.strike_expiries is not None:
            strikes_by_expiry: dict[str, set[int]] = {}
            for strike, expiries in self.strike_expiries.items():
                for expiry in expiries:
                    strikes_by_expiry.setdefault(expiry, set()).add(strike)
                    selected_pairs.append((strike, expiry))
            for expiry, selected_strikes in strikes_by_expiry.items():
                payload = fetcher.fetch_chain(self.symbol, expiry)
                rows.extend(
                    extract_strike_rows(
                        payload,
                        self.symbol,
                        expiry,
                        now,
                        selected_strikes,
                    )
                )
            rows_by_strike: dict[int | tuple[int, str], list[dict]] = {}
        else:
            payload = fetcher.fetch_chain(self.symbol, self.expiry)
            expiry_value = self._resolve_expiry(payload)
            selected = self._resolve_strikes(payload)
            rows.extend(
                extract_strike_rows(payload, self.symbol, expiry_value, now, set(selected))
            )

        if not rows:
            return f"No option rows found for {self.symbol} and the configured expiries at {now:%H:%M:%S}"

        inserted = self.store.insert_rows(rows)
        if self.strike_expiries is not None:
            rows_by_strike = {
                pair: self.store.fetch_rows_for_strike(self.symbol, pair[1], pair[0])
                for pair in selected_pairs
            }
            expiry_description = ", ".join(
                f"{strike}: {', '.join(expiries)}"
                for strike, expiries in self.strike_expiries.items()
            )
        else:
            persisted_rows = self.store.fetch_rows_for_symbol(self.symbol, expiry_value, selected)
            rows_by_strike = {strike: persisted_rows.get(strike, []) for strike in selected}
            expiry_description = expiry_value
        if self.workbook_publisher is not None:
            workbook_path = self.workbook_publisher(self.symbol, rows_by_strike, now)
        else:
            workbook_path = write_daily_workbook(
                self.output_dir,
                self.symbol,
                rows_by_strike,
                trade_date=now,
            )
        return (
            f"Processed {self.symbol} expiries [{expiry_description}] at {now:%H:%M:%S}; "
            f"inserted={inserted}; workbook={workbook_path}"
        )
