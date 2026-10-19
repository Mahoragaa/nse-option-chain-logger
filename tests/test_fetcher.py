from datetime import date, timedelta

import pytest

from nse_oi_logger.fetcher import NseFetcher


def test_fetch_chain_formats_expiry_for_nse(monkeypatch):
    fetcher = NseFetcher()
    calls = []

    def fake_request(endpoint, params):
        calls.append((endpoint, params))
        return {"records": {"data": [{}]}}

    monkeypatch.setattr(fetcher, "_request_json", fake_request)
    requested = date.today() + timedelta(days=10)
    fetcher.fetch_chain("NIFTY", requested.isoformat())

    month_names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    expected = f"{requested.day:02d}-{month_names[requested.month - 1]}-{requested.year}"
    assert calls == [
        (
            NseFetcher.INDEX_ENDPOINT,
            {"type": "Indices", "symbol": "NIFTY", "expiry": expected},
        )
    ]


def test_fetch_chain_rejects_expiry_not_listed_by_nse(monkeypatch):
    fetcher = NseFetcher()
    requested = date.today() + timedelta(days=1)
    available = requested + timedelta(days=7)
    month_names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    available_text = (
        f"{available.day:02d}-{month_names[available.month - 1]}-{available.year}"
    )

    def fake_request(endpoint, params):
        assert endpoint == NseFetcher.INDEX_ENDPOINT
        assert params["expiry"] == (
            f"{requested.day:02d}-{month_names[requested.month - 1]}-{requested.year}"
        )
        return {"records": {"data": [], "expiryDates": [available_text]}}

    monkeypatch.setattr(fetcher, "_request_json", fake_request)

    with pytest.raises(ValueError, match="not an expiry listed by NSE"):
        fetcher.fetch_chain("NIFTY", requested.isoformat())


def test_cookie_refresh_uses_the_working_option_chain_page(monkeypatch):
    fetcher = NseFetcher()
    requested_urls = []
    requested_options = []

    class Response:
        status_code = 200

        @staticmethod
        def raise_for_status():
            return None

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        requested_options.append(kwargs)
        return Response()

    monkeypatch.setattr(fetcher.session, "get", fake_get)
    fetcher.refresh_cookies()

    assert requested_urls == ["https://www.nseindia.com/option-chain"]
    assert requested_options[0]["allow_redirects"] is True
