# NSE Option Chain Logger

This project is a desktop application for logging live NSE option-chain data into an Excel workbook during market hours.

## Features

- Polls the NSE option-chain endpoint once per cycle
- Supports NIFTY, BANKNIFTY, FINNIFTY and equity symbols
- Tracks selected strikes in per-strike worksheets
- Saves one workbook per trading day
- Uses SQLite as the durable source of truth
- Uses a scheduler aligned to 3-minute market slots
- Provides Excel output with formatting and charts

## Quick start

1. Create a virtual environment.
2. Install dependencies:
   pip install requests pandas openpyxl xlsxwriter APScheduler PyYAML
3. Run:
   python -m nse_oi_logger.main

## Files

- `nse_oi_logger/` package source
- `tests/` unit tests
- `config.yaml` runtime configuration
