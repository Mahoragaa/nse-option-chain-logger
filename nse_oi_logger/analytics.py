from __future__ import annotations

from typing import Any


def classify_build_up(call_ltp_delta: float, put_ltp_delta: float, call_oi_delta: float, put_oi_delta: float) -> str:
    """Return a compact build-up classification for a single strike.

    This logic is intentionally simple and deterministic for intraday analysis.
    It keys off whether call-side or put-side evidence dominates the move.
    """
    if call_ltp_delta > 0 and call_oi_delta > 0 and put_ltp_delta > 0 and put_oi_delta > 0:
        if (call_oi_delta - put_oi_delta) > 0:
            return "Long Build-up"
        return "Short Build-up"

    if call_ltp_delta > 0 and put_ltp_delta > 0 and call_oi_delta < 0 and put_oi_delta < 0:
        if abs(call_oi_delta) > abs(put_oi_delta):
            return "Long Unwinding"
        return "Short Covering"

    if call_ltp_delta < 0 and put_ltp_delta < 0 and call_oi_delta > 0 and put_oi_delta > 0:
        if abs(call_oi_delta) > abs(put_oi_delta):
            return "Short Build-up"
        return "Long Build-up"

    if call_ltp_delta < 0 and put_ltp_delta < 0 and call_oi_delta < 0 and put_oi_delta < 0:
        if abs(call_oi_delta) > abs(put_oi_delta):
            return "Short Covering"
        return "Long Unwinding"

    avg_price_delta = (call_ltp_delta + put_ltp_delta) / 2.0
    avg_oi_delta = (call_oi_delta + put_oi_delta) / 2.0
    if avg_price_delta > 0 and avg_oi_delta > 0:
        return "Long Build-up"
    if avg_price_delta > 0 and avg_oi_delta < 0:
        return "Long Unwinding"
    if avg_price_delta < 0 and avg_oi_delta > 0:
        return "Short Build-up"
    if avg_price_delta < 0 and avg_oi_delta < 0:
        return "Short Covering"
    return "Neutral"


def get_bias(scores: dict[str, Any]) -> str:
    bullish_score = float(scores.get("bullish_score", 0.0))
    bearish_score = float(scores.get("bearish_score", 0.0))
    if bullish_score >= 2 and bullish_score > bearish_score:
        return "Bullish"
    if bearish_score >= 2 and bearish_score > bullish_score:
        return "Bearish"
    return "Neutral"
