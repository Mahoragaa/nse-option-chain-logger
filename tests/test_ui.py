from datetime import date

from nse_oi_logger.ui import build_default_settings


def test_default_settings_leave_strikes_blank():
    assert build_default_settings().expiry == date.today().isoformat()
    assert build_default_settings().strikes == ""
