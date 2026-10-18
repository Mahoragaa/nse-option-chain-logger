from nse_oi_logger.parser import compute_auto_atm_strikes


def test_auto_atm_strikes():
    strikes = compute_auto_atm_strikes(24560, step=100, window=2)
    assert strikes == [24400, 24500, 24600, 24700, 24800]
