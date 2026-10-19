from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from threading import Event

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from nse_oi_logger.excel_live import ExcelLiveWorkbook
from nse_oi_logger.orchestrator import OptionChainLogger
from nse_oi_logger.selection import parse_strike_expiries, validate_expiry_date
from nse_oi_logger.ui import OptionChainApp


def parse_strike_list(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(v.strip()) for v in raw.split(",") if v.strip()]


def run_once(
    symbol: str,
    expiry: str | None,
    strikes: list[int],
    db_path: str = "data/option_chain.db",
    output_dir: str = "output",
    auto_atm: bool = False,
    atm_window: int = 2,
    strike_expiries: dict[int, list[str]] | None = None,
) -> str:
    logger = OptionChainLogger(
        symbol=symbol,
        expiry=expiry,
        strikes=strikes,
        db_path=db_path,
        output_dir=output_dir,
        auto_atm=auto_atm,
        atm_window=atm_window,
        strike_expiries=strike_expiries,
    )
    result = logger.process_cycle()
    print(result)
    return result


def start_scheduler(
    symbol: str,
    expiry: str | None,
    strikes: list[int],
    db_path: str = "data/option_chain.db",
    output_dir: str = "output",
    auto_atm: bool = False,
    atm_window: int = 2,
    on_status: Callable[[str], None] | None = None,
    live_excel: bool = False,
    strike_expiries: dict[int, list[str]] | None = None,
    stop_event: Event | None = None,
) -> None:
    excel_workbook = ExcelLiveWorkbook(output_dir) if live_excel else None
    logger = OptionChainLogger(
        symbol=symbol,
        expiry=expiry,
        strikes=strikes,
        db_path=db_path,
        output_dir=output_dir,
        auto_atm=auto_atm,
        atm_window=atm_window,
        workbook_publisher=excel_workbook.publish if excel_workbook else None,
        strike_expiries=strike_expiries,
    )
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
        logger.process_cycle,
        trigger=CronTrigger(hour="9-15", minute="*/3", day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="nse_option_cycle",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    def report_job_result(event):
        if on_status is None:
            return
        if event.exception:
            on_status(f"Scheduled cycle failed: {event.exception}")
        else:
            on_status(str(event.retval))

    scheduler.add_listener(report_job_result, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    print("Scheduler started. Press Ctrl+C to stop.")
    if on_status is not None:
        on_status("Schedule started; waiting for the next 3-minute market slot.")
    try:
        scheduler.start()
        if stop_event is None:
            while True:
                time.sleep(0.25)
        else:
            stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown(wait=True)
        if excel_workbook is not None:
            excel_workbook.close()
        if on_status is not None:
            on_status("Schedule stopped.")
        print("Scheduler stopped.")


def launch_ui() -> None:
    def run_once_from_ui(
        symbol: str,
        selection_entries: list[tuple[str, str]],
    ) -> str:
        strike_expiries = parse_strike_expiries(selection_entries)
        return run_once(symbol, None, [], strike_expiries=strike_expiries)

    def schedule_from_ui(
        symbol: str,
        selection_entries: list[tuple[str, str]],
        on_status: Callable[[str], None],
        stop_event: Event,
    ) -> str:
        strike_expiries = parse_strike_expiries(selection_entries)
        start_scheduler(
            symbol,
            None,
            [],
            on_status=on_status,
            live_excel=True,
            strike_expiries=strike_expiries,
            stop_event=stop_event,
        )
        return "Schedule stopped."

    app = OptionChainApp(run_once_callback=run_once_from_ui, schedule_callback=schedule_from_ui)
    app.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="NSE option-chain intraday logger")
    parser.add_argument("--symbol", default="NIFTY")
    parser.add_argument("--expiry", default=None)
    parser.add_argument("--strikes", default="")
    parser.add_argument("--db", default="data/option_chain.db")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--auto-atm", action="store_true", help="Add ATM +/- N strikes around the current spot")
    parser.add_argument("--atm-window", type=int, default=2, help="Range around the ATM strike when auto-atm is enabled")
    parser.add_argument("--schedule", action="store_true", help="Run continuously on the 3-minute NSE market schedule")
    parser.add_argument("--run-once", action="store_true", help="Process a single market cycle and exit")
    parser.add_argument("--ui", action="store_true", help="Launch the simple desktop UI")
    args = parser.parse_args()

    strikes = parse_strike_list(args.strikes)

    if args.schedule:
        if args.expiry:
            args.expiry = validate_expiry_date(args.expiry)
        if not strikes and not args.auto_atm:
            raise ValueError("You must provide at least one strike value or enable --auto-atm")
        start_scheduler(args.symbol, args.expiry, strikes, args.db, args.output_dir, args.auto_atm, args.atm_window)
        return
    if args.run_once:
        if args.expiry:
            args.expiry = validate_expiry_date(args.expiry)
        if not strikes and not args.auto_atm:
            raise ValueError("You must provide at least one strike value or enable --auto-atm")
        run_once(args.symbol, args.expiry, strikes, args.db, args.output_dir, args.auto_atm, args.atm_window)
        return
    if args.ui:
        launch_ui()
        return

    launch_ui()


if __name__ == "__main__":
    main()
