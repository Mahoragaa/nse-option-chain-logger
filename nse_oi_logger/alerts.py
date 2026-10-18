from __future__ import annotations

from typing import Iterable


def evaluate_alerts(rows: Iterable[dict], oi_threshold: float = 0.0, pcr_threshold: float = 0.0) -> list[str]:
    alerts: list[str] = []
    for row in rows:
        call_delta = float(row.get("call_change_oi", 0) or 0)
        put_delta = float(row.get("put_change_oi", 0) or 0)
        pcr = float(row.get("pcr", 0) or 0)
        if abs(call_delta) >= oi_threshold or abs(put_delta) >= oi_threshold:
            alerts.append(f"Large OI move at strike {row.get('strike')}: {call_delta}/{put_delta}")
        if pcr >= pcr_threshold:
            alerts.append(f"PCR threshold crossed at strike {row.get('strike')}: {pcr}")
    return alerts


def evaluate_strike_bias(row: dict) -> str:
    call_delta = float(row.get("call_change_oi", 0) or 0)
    put_delta = float(row.get("put_change_oi", 0) or 0)
    net = put_delta - call_delta
    if net > 0:
        return "Bullish"
    if net < 0:
        return "Bearish"
    return "Neutral"
