from __future__ import annotations

import json
import time
from typing import Any

import requests


class NseFetcher:
    """Fetch option chain data from NSE with a browser-like requests session."""

    INDEX_ENDPOINT = "https://www.nseindia.com/api/option-chain-indices"
    EQUITY_ENDPOINT = "https://www.nseindia.com/api/option-chain-equities"

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
        homepage = self.session.get("https://www.nseindia.com/", timeout=self.timeout, allow_redirects=True)
        homepage.raise_for_status()

    def _request_json(self, endpoint: str) -> dict[str, Any]:
        self.refresh_cookies()
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.session.get(endpoint, timeout=self.timeout)
                if response.status_code == 403:
                    self.refresh_cookies()
                    response = self.session.get(endpoint, timeout=self.timeout)
                if response.status_code != 200:
                    raise requests.HTTPError(f"Unexpected status {response.status_code}")
                parsed = response.json()
                if not isinstance(parsed, dict):
                    raise ValueError("Unexpected JSON payload")
                records = parsed.get("records") or {}
                if not isinstance(records, dict):
                    raise ValueError("The NSE response is missing a valid records payload")
                if not records.get("data"):
                    raise ValueError("The NSE response is empty or missing data")
                return parsed
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
        endpoint = self._chain_endpoint(symbol)
        payload = self._request_json(endpoint)
        records = payload.get("records") or {}
        expiry_dates = records.get("expiryDates") or []
        return [str(expiry) for expiry in expiry_dates if expiry]

    def _chain_endpoint(self, symbol: str) -> str:
        symbol = symbol.upper()
        if symbol in {"NIFTY", "BANKNIFTY", "FINNIFTY"}:
            return f"{self.INDEX_ENDPOINT}?symbol={symbol}"
        return f"{self.EQUITY_ENDPOINT}?symbol={symbol}"

    def fetch_chain(self, symbol: str, expiry: str | None = None) -> dict[str, Any]:
        endpoint = self._chain_endpoint(symbol)
        payload = self._request_json(endpoint)
        if expiry is not None:
            return payload
        return payload
