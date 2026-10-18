from nse_oi_logger.analytics import classify_build_up, get_bias


def test_classify_build_up():
    assert classify_build_up(10.0, 9.0, 120, 50) == "Long Build-up"
    assert classify_build_up(9.0, 10.0, -100, -40) == "Long Unwinding"
    assert classify_build_up(8.0, 9.0, 50, 120) == "Short Build-up"
    assert classify_build_up(10.0, 9.0, -50, -120) == "Short Covering"


def test_get_bias():
    assert get_bias({"bullish_score": 3, "bearish_score": 0}) == "Bullish"
    assert get_bias({"bullish_score": 0, "bearish_score": 3}) == "Bearish"
    assert get_bias({"bullish_score": 1, "bearish_score": 1}) == "Neutral"
