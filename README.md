# NSE Option Chain Logger

This project is a desktop application for logging live NSE option-chain data into an Excel workbook during market hours.

## Features

- Polls the NSE option-chain endpoint once per cycle
- Supports NIFTY, BANKNIFTY, FINNIFTY and equity symbols
- Tracks selected strike/expiry combinations in separate worksheets
- Saves one workbook per trading day
- Opens the daily workbook in Microsoft Excel when scheduling from the UI and updates it after each successful cycle
- Uses SQLite as the durable source of truth
- Uses a scheduler aligned to 3-minute market slots
- Provides Excel output with formatting and charts

## Quick start

1. Create a virtual environment.
2. Install dependencies:
   pip install requests pandas openpyxl xlsxwriter APScheduler PyYAML pywin32
3. Run:
   python -m nse_oi_logger.main

The UI does not require a browser or the NSE website to be open. NSE must still
allow the app's data request; if NSE returns HTTP 403, the app cannot retrieve
market data and reports that restriction in the status message.

Add one row per strike in the UI and enter one or more comma-separated expiry
dates for that strike. Expiry dates must be today or later and must be dates
listed by NSE for the selected symbol. Use the calendar button to append dates.

The UI's **Start schedule** action requires desktop Microsoft Excel and `pywin32`.
It opens the daily workbook after the first successful data fetch and saves each
subsequent cycle into that same open workbook. The scheduler runs every three
minutes during market hours; each configured strike/expiry pair is fetched on
each cycle. Use **Stop schedule** to stop future polls while leaving the UI open.
If Excel disconnects, the app reconnects and retries the workbook update before
reporting a failure.

## Files

- `nse_oi_logger/` package source
- `tests/` unit tests
- `config.yaml` runtime configuration
