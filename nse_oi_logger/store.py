from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


class SQLiteStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS option_rows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    expiry TEXT NOT NULL,
                    strike INTEGER NOT NULL,
                    time_slot TEXT NOT NULL,
                    underlying_spot REAL,
                    call_oi INTEGER,
                    call_change_oi INTEGER,
                    put_oi INTEGER,
                    put_change_oi INTEGER,
                    call_ltp REAL,
                    put_ltp REAL,
                    call_volume INTEGER,
                    put_volume INTEGER,
                    call_iv REAL,
                    put_iv REAL,
                    pcr REAL,
                    net_change_oi INTEGER,
                    UNIQUE(symbol, expiry, strike, time_slot)
                )
                """
            )
            conn.commit()

    def insert_rows(self, rows: Iterable[dict]) -> int:
        inserted = 0
        with sqlite3.connect(self.db_path) as conn:
            for row in rows:
                try:
                    conn.execute(
                        """
                        INSERT INTO option_rows (
                            symbol, expiry, strike, time_slot, underlying_spot, call_oi,
                            call_change_oi, put_oi, put_change_oi, call_ltp, put_ltp,
                            call_volume, put_volume, call_iv, put_iv, pcr, net_change_oi
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["symbol"],
                            row["expiry"],
                            row["strike"],
                            row["time_slot"],
                            row.get("underlying_spot"),
                            row.get("call_oi"),
                            row.get("call_change_oi"),
                            row.get("put_oi"),
                            row.get("put_change_oi"),
                            row.get("call_ltp"),
                            row.get("put_ltp"),
                            row.get("call_volume"),
                            row.get("put_volume"),
                            row.get("call_iv"),
                            row.get("put_iv"),
                            row.get("pcr"),
                            row.get("net_change_oi"),
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue
            conn.commit()
        return inserted

    def fetch_rows_for_strike(self, symbol: str, expiry: str, strike: int) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            result = conn.execute(
                """
                SELECT * FROM option_rows
                WHERE symbol = ? AND expiry = ? AND strike = ?
                ORDER BY id ASC
                """,
                (symbol, expiry, strike),
            ).fetchall()
        return [dict(r) for r in result]

    def fetch_rows_for_symbol(self, symbol: str, expiry: str, strikes: list[int] | None = None) -> dict[int, list[dict]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if strikes:
                placeholders = ", ".join("?" for _ in strikes)
                query = (
                    "SELECT * FROM option_rows WHERE symbol = ? AND expiry = ? AND strike IN (%s) ORDER BY id ASC"
                    % placeholders
                )
                params: tuple = (symbol, expiry, *strikes)
                rows = conn.execute(query, params).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM option_rows WHERE symbol = ? AND expiry = ? ORDER BY id ASC",
                    (symbol, expiry),
                ).fetchall()

        grouped: dict[int, list[dict]] = {}
        for row in rows:
            key = int(row["strike"])
            grouped.setdefault(key, []).append(dict(row))
        return grouped
