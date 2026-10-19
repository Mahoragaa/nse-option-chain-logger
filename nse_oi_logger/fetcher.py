from __future__ import annotations

import json
import time
from datetime import date, datetime
from typing import Any

import requests


class NseFetcher:
    """Fetch option chain data from NSE with a browser-like requests session."""

    INDEX_ENDPOINT = "https://www.nseindia.com/api/option-chain-v3"
    EQUITY_ENDPOINT = "https://www.nseindia.com/api/option-chain-v3"
    CONTRACT_INFO_ENDPOINT = "https://www.nseindia.com/api/option-chain-contract-info"

    DEFAULT_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    def refresh_cookies(self) -> None:
        homepage = self.session.get(
            "https://www.nseindia.com/option-chain",
            timeout=self.timeout,
            allow_redirects=True,
        )
        if homepage.status_code == 403:
            raise RuntimeError(
                "NSE denied access to its website (HTTP 403). The data provider is blocking "
                "this request; the app cannot fetch or update market data until NSE permits it."
            )
        homepage.raise_for_status()

    def _request_json(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                self.refresh_cookies()
                response = self.session.get(endpoint, params=params, timeout=self.timeout)
                if response.status_code == 403:
                    raise RuntimeError(
                        "NSE denied access to its option-chain API (HTTP 403). "
                        "The app cannot fetch or update market data until NSE permits it."
                    )
                if response.status_code != 200:
                    raise requests.HTTPError(f"Unexpected status {response.status_code}")
                parsed = response.json()
                if not isinstance(parsed, dict):
                    raise ValueError("Unexpected JSON payload")
                records = parsed.get("records")
                if records is not None and not isinstance(records, dict):
                    raise ValueError("The NSE response has an invalid records payload")
                if isinstance(records, dict) and not isinstance(records.get("data", []), list):
                    raise ValueError("The NSE response has an invalid option data list")
                return parsed
            except RuntimeError:
                raise
            except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Unable to fetch option chain data after retries: {exc}") from exc
        if last_error is not None:
            raise RuntimeError(f"Unable to fetch option chain data: {last_error}")
        raise RuntimeError("Unable to fetch option chain data")

    def fetch_expiries(self, symbol: str) -> list[str]:
        payload = self._request_json(self.CONTRACT_INFO_ENDPOINT, {"symbol": symbol.upper()})
        expiry_dates = payload.get("expiryDates") or []
        return [str(expiry) for expiry in expiry_dates if expiry]

    def _chain_endpoint(self) -> str:
        return self.INDEX_ENDPOINT

    def fetch_chain(self, symbol: str, expiry: str | None = None) -> dict[str, Any]:
        symbol = symbol.upper()
        indices = {"NIFTY", "BANKNIFTY", "FINNIFTY"}
        if expiry is None:
            available_expiries = self.fetch_expiries(symbol)
            if not available_expiries:
                raise RuntimeError(f"NSE did not provide expiry dates for {symbol}.")
            expiry = _canonical_expiry(available_expiries[0])

        expiry_date = date.fromisoformat(expiry)
        month = (
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        )[expiry_date.month - 1]
        nse_expiry = f"{expiry_date.day:02d}-{month}-{expiry_date.year}"
        payload = self._request_json(
            self._chain_endpoint(),
            {
                "type": "Indices" if symbol in indices else "Equity",
                "symbol": symbol,
                "expiry": nse_expiry,
            },
        )
        available = payload.get("records", {}).get("expiryDates") or []
        if available and expiry not in {_canonical_expiry(str(value)) for value in available}:
            raise ValueError(f"{expiry} is not an expiry listed by NSE for {symbol}.")
        return payload


def _canonical_expiry(value: str) -> str:
    for date_format in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue
    return value
