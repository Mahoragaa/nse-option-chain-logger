from datetime import datetime

from nse_oi_logger.parser import normalize_option_row


def test_normalize_option_row():
    payload = {
        "strikePrice": 24500,
        "CE": {
            "openInterest": 1200,
            "changeinOpenInterest": 80,
            "lastPrice": 125.5,
            "totalTradedVolume": 400,
            "impliedVolatility": 15.2,
        },
        "PE": {
            "openInterest": 900,
            "changeinOpenInterest": -60,
            "lastPrice": 100.2,
            "totalTradedVolume": 350,
            "impliedVolatility": 17.8,
        },
        "timestamp": "2026-10-18T09:18:00+05:30",
        "underlyingValue": 24550,
    }

    result = normalize_option_row(payload, "NIFTY", "2026-10-28", datetime(2026, 10, 18, 9, 18, 0), 24500)

    assert result["symbol"] == "NIFTY"
    assert result["expiry"] == "2026-10-28"
    assert result["strike"] == 24500
    assert result["call_oi"] == 1200
    assert result["put_oi"] == 900
    assert result["time_slot"] == "09:18:00"
    assert result["pcr"] == 0.75
    assert result["net_change_oi"] == -140
