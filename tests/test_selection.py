from datetime import date, timedelta

import pytest

from nse_oi_logger.selection import parse_strike_expiries, validate_expiry_date


def test_parse_multiple_expiries_per_strike():
    today = date.today()
    first_expiry = (today + timedelta(days=2)).isoformat()
    second_expiry = (today + timedelta(days=9)).isoformat()
    third_expiry = (today + timedelta(days=16)).isoformat()

    result = parse_strike_expiries([
        ("23000", f"{first_expiry}, {second_expiry}"),
        ("22900", third_expiry),
    ])

    assert result == {
        23000: [first_expiry, second_expiry],
        22900: [third_expiry],
    }


def test_expiry_must_not_be_in_the_past():
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    with pytest.raises(ValueError, match="in the past"):
        validate_expiry_date(yesterday)


def test_strike_requires_at_least_one_expiry():
    with pytest.raises(ValueError, match="at least one expiry"):
        parse_strike_expiries([("23000", "")])


def test_invalid_expiry_format_is_rejected():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_strike_expiries([("23000", "10/25/2026")])
