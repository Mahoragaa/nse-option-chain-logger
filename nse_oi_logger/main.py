from __future__ import annotations

import argparse

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from nse_oi_logger.orchestrator import OptionChainLogger
from nse_oi_logger.ui import OptionChainApp


def parse_strike_list(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(v.strip()) for v in raw.split(",") if v.strip()]


def run_once(symbol: str, expiry: str | None, strikes: list[int], db_path: str = "data/option_chain.db", output_dir: str = "output", auto_atm: bool = False, atm_window: int = 2) -> None:
    logger = OptionChainLogger(symbol=symbol, expiry=expiry, strikes=strikes, db_path=db_path, output_dir=output_dir, auto_atm=auto_atm, atm_window=atm_window)
    result = logger.process_cycle()
    print(result)


def start_scheduler(symbol: str, expiry: str | None, strikes: list[int], db_path: str = "data/option_chain.db", output_dir: str = "output", auto_atm: bool = False, atm_window: int = 2) -> None:
    logger = OptionChainLogger(symbol=symbol, expiry=expiry, strikes=strikes, db_path=db_path, output_dir=output_dir, auto_atm=auto_atm, atm_window=atm_window)
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
        logger.process_cycle,
        trigger=CronTrigger(hour="9-15", minute="*/3", day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="nse_option_cycle",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    print("Scheduler started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)
        print("Scheduler stopped.")


def launch_ui() -> None:
    app = OptionChainApp(run_once_callback=run_once, schedule_callback=start_scheduler)
    app.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="NSE option-chain intraday logger")
    parser.add_argument("--symbol", default="NIFTY")
    parser.add_argument("--expiry", default=None)
    parser.add_argument("--strikes", default="24500,24600,24700")
    parser.add_argument("--db", default="data/option_chain.db")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--auto-atm", action="store_true", help="Add ATM +/- N strikes around the current spot")
    parser.add_argument("--atm-window", type=int, default=2, help="Range around the ATM strike when auto-atm is enabled")
    parser.add_argument("--schedule", action="store_true", help="Run continuously on the 3-minute NSE market schedule")
    parser.add_argument("--run-once", action="store_true", help="Process a single market cycle and exit")
    parser.add_argument("--ui", action="store_true", help="Launch the simple desktop UI")
    args = parser.parse_args()

    strikes = parse_strike_list(args.strikes)
    if not strikes and not args.auto_atm:
        raise ValueError("You must provide at least one strike value or enable --auto-atm")

    if args.schedule:
        start_scheduler(args.symbol, args.expiry, strikes, args.db, args.output_dir, args.auto_atm, args.atm_window)
        return
    if args.run_once:
        run_once(args.symbol, args.expiry, strikes, args.db, args.output_dir, args.auto_atm, args.atm_window)
        return
    if args.ui:
        launch_ui()
        return

    launch_ui()


if __name__ == "__main__":
    main()
