from __future__ import annotations

from datetime import datetime
from typing import Any


def _canonical_expiry(value: str) -> str:
    for date_format in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, date_format).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_auto_atm_strikes(spot_price: float, step: int = 100, window: int = 2) -> list[int]:
    if spot_price <= 0:
        return []
    atm = round(spot_price / step) * step
    return [atm + offset * step for offset in range(-window, window + 1)]


def normalize_option_row(payload: dict[str, Any], symbol: str, expiry: str, slot_dt: datetime, strike: int) -> dict[str, Any]:
    ce = payload.get("CE") or {}
    pe = payload.get("PE") or {}
    call_oi = int(_safe_float(ce.get("openInterest"), 0))
    put_oi = int(_safe_float(pe.get("openInterest"), 0))
    call_change_oi = int(_safe_float(ce.get("changeinOpenInterest"), 0))
    put_change_oi = int(_safe_float(pe.get("changeinOpenInterest"), 0))
    underlying_value = _safe_float(payload.get("underlyingValue"), 0.0)
    call_ltp = _safe_float(ce.get("lastPrice"), 0.0)
    put_ltp = _safe_float(pe.get("lastPrice"), 0.0)
    call_volume = int(_safe_float(ce.get("totalTradedVolume"), 0))
    put_volume = int(_safe_float(pe.get("totalTradedVolume"), 0))
    call_iv = _safe_float(ce.get("impliedVolatility"), 0.0)
    put_iv = _safe_float(pe.get("impliedVolatility"), 0.0)

    pcr = (put_oi / call_oi) if call_oi else 0.0

    return {
        "symbol": symbol,
        "expiry": expiry,
        "strike": int(strike),
        "time_slot": slot_dt.strftime("%H:%M:%S"),
        "time_dt": slot_dt,
        "underlying_spot": underlying_value,
        "call_oi": call_oi,
        "call_change_oi": call_change_oi,
        "put_oi": put_oi,
        "put_change_oi": put_change_oi,
        "call_ltp": call_ltp,
        "put_ltp": put_ltp,
        "call_volume": call_volume,
        "put_volume": put_volume,
        "call_iv": call_iv,
        "put_iv": put_iv,
        "pcr": pcr,
        "net_change_oi": put_change_oi - call_change_oi,
    }


def extract_strike_rows(
    raw_data: dict[str, Any],
    symbol: str,
    expiry: str,
    slot_dt: datetime,
    selected_strikes: set[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in raw_data.get("records", {}).get("data", []) or []:
        strike = int(_safe_float(item.get("strikePrice"), 0))
        if strike not in selected_strikes:
            continue
        item_expiry = item.get("expiryDate") or item.get("expiryDates")
        if item_expiry and _canonical_expiry(str(item_expiry)) != _canonical_expiry(expiry):
            continue
        rows.append(normalize_option_row(item, symbol, expiry, slot_dt, strike))
    return rows
