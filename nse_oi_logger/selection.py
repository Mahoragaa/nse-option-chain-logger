from __future__ import annotations

from datetime import date


def validate_expiry_date(value: str) -> str:
    try:
        expiry = date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"Expiry {value!r} must use YYYY-MM-DD format.") from exc
    if expiry < date.today():
        raise ValueError(f"Expiry {expiry.isoformat()} is in the past.")
    return expiry.isoformat()


def parse_strike_expiries(entries: list[tuple[str, str]]) -> dict[int, list[str]]:
    selections: dict[int, list[str]] = {}
    for raw_strike, raw_expiries in entries:
        if not raw_strike.strip() and not raw_expiries.strip():
            continue
        try:
            strike = int(raw_strike.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid strike value: {raw_strike!r}") from exc
        if strike <= 0:
            raise ValueError(f"Strike must be a positive number: {strike}")
        if strike in selections:
            raise ValueError(f"Strike {strike} is listed more than once.")

        expiry_values = [value.strip() for value in raw_expiries.split(",") if value.strip()]
        if not expiry_values:
            raise ValueError(f"Add at least one expiry for strike {strike}.")

        expiries: list[str] = []
        for value in expiry_values:
            iso_expiry = validate_expiry_date(value)
            if iso_expiry not in expiries:
                expiries.append(iso_expiry)
        selections[strike] = expiries

    if not selections:
        raise ValueError("Add at least one strike and expiry.")
    return selections
