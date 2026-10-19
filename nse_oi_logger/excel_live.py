from __future__ import annotations

import queue
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from nse_oi_logger.excel_writer import (
    StrikeExpiry,
    build_summary_metrics,
    strike_sheet_name,
    write_daily_workbook,
)

logger = logging.getLogger(__name__)


@dataclass
class _UpdateRequest:
    workbook_path: Path
    rows_by_strike: dict[StrikeExpiry, list[dict]]
    completed: threading.Event = field(default_factory=threading.Event)
    error: Exception | None = None


class ExcelLiveWorkbook:
    """Publish workbook updates through Excel COM so the open workbook stays live."""

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self._requests: queue.Queue[_UpdateRequest | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._started = False
        self._lock = threading.Lock()
        self._workbook_path: Path | None = None
        self._workbook_date: str | None = None

    def publish(
        self,
        symbol: str,
        rows_by_strike: dict[StrikeExpiry, list[dict]],
        trade_date: datetime,
    ) -> str:
        trade_date_key = trade_date.strftime("%Y-%m-%d")
        with self._lock:
            if self._workbook_date != trade_date_key:
                self._workbook_path = Path(
                    write_daily_workbook(self.output_dir, symbol, rows_by_strike, trade_date)
                )
                self._workbook_date = trade_date_key
            if not self._started:
                self._thread.start()
                self._started = True

        if self._workbook_path is None:
            raise RuntimeError("Live Excel workbook path was not initialized")
        request = _UpdateRequest(self._workbook_path, rows_by_strike)
        self._requests.put(request)
        request.completed.wait()
        if request.error is not None:
            raise RuntimeError(f"Unable to update live Excel workbook: {request.error}") from request.error
        return str(self._workbook_path)

    def close(self) -> None:
        if not self._started:
            return
        self._requests.put(None)
        self._thread.join()
        self._started = False

    def _run(self) -> None:
        try:
            import pythoncom
            import win32com.client
        except Exception as exc:
            while True:
                request = self._requests.get()
                if request is None:
                    return
                request.error = RuntimeError(
                    f"Unable to initialize live Excel automation: {exc}"
                )
                request.completed.set()

        pythoncom.CoInitialize()
        excel: Any = None
        workbook: Any = None
        current_path: Path | None = None
        try:
            while True:
                request = self._requests.get()
                if request is None:
                    break
                for attempt in range(3):
                    try:
                        if excel is None:
                            excel = win32com.client.DispatchEx("Excel.Application")
                            excel.Visible = True
                            excel.DisplayAlerts = False

                        if current_path != request.workbook_path:
                            workbook = excel.Workbooks.Open(str(request.workbook_path.resolve()))
                            current_path = request.workbook_path

                        self._update_workbook(workbook, request.rows_by_strike)
                        workbook.Save()
                        request.error = None
                        break
                    except Exception as exc:
                        request.error = exc
                        if attempt < 2 and self._is_disconnected_error(exc):
                            logger.warning(
                                "Excel COM disconnected; reopening Excel and retrying "
                                "the workbook update (attempt %s).",
                                attempt + 2,
                            )
                            self._close_excel(workbook, excel)
                            workbook = None
                            excel = None
                            current_path = None
                            continue
                        break
                request.completed.set()
        finally:
            self._close_excel(workbook, excel)
            pythoncom.CoUninitialize()

    @staticmethod
    def _close_excel(workbook: Any, excel: Any) -> None:
        if workbook is not None:
            try:
                workbook.Save()
                workbook.Close(SaveChanges=True)
            except Exception:
                logger.warning("Could not close the live Excel workbook cleanly.", exc_info=True)
        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                logger.warning("Could not close the Excel automation instance cleanly.", exc_info=True)

    @staticmethod
    def _is_disconnected_error(error: Exception) -> bool:
        return (
            getattr(error, "hresult", None) == -2147417848
            or bool(error.args and error.args[0] == -2147417848)
        )

    @staticmethod
    def _update_workbook(
        workbook: Any,
        rows_by_strike: dict[StrikeExpiry, list[dict]],
    ) -> None:
        desired_sheets = {"Summary", *(strike_sheet_name(key) for key in rows_by_strike)}
        workbook.Application.DisplayAlerts = False
        for sheet in list(workbook.Worksheets):
            if sheet.Name not in desired_sheets:
                sheet.Delete()

        summary = workbook.Worksheets("Summary")
        metrics = build_summary_metrics(rows_by_strike)
        summary.Cells.ClearContents()
        summary_values = (("Metric", "Value"), *tuple(metrics.items()))
        summary.Range(
            summary.Cells(1, 1),
            summary.Cells(len(summary_values), 2),
        ).Value = summary_values

        for strike_key, rows in rows_by_strike.items():
            sheet_name = strike_sheet_name(strike_key)
            if sheet_name not in [sheet.Name for sheet in workbook.Worksheets]:
                sheet = workbook.Worksheets.Add(After=workbook.Worksheets(workbook.Worksheets.Count))
                sheet.Name = sheet_name
            else:
                sheet = workbook.Worksheets(sheet_name)

            sheet.Cells.ClearContents()
            headers = ["Time", "Strike", "Call OI", "Call Change in OI", "Put OI", "Put Change in OI"]
            if isinstance(strike_key, tuple):
                headers.append("Expiry")
            values = [tuple(headers)]
            for row in rows:
                values.append((
                    row.get("time_slot"),
                    row.get("strike"),
                    row.get("call_oi"),
                    row.get("call_change_oi"),
                    row.get("put_oi"),
                    row.get("put_change_oi"),
                    *((row.get("expiry", strike_key[1]),) if isinstance(strike_key, tuple) else ()),
                ))
            sheet.Range(
                sheet.Cells(1, 1),
                sheet.Cells(len(values), len(headers)),
            ).Value = values
            sheet.Range(
                sheet.Cells(1, 1),
                sheet.Cells(len(values), len(headers)),
            ).HorizontalAlignment = -4108
            sheet.AutoFilterMode = False
            sheet.Range(sheet.Cells(1, 1), sheet.Cells(len(values), len(headers))).AutoFilter()
            sheet.Columns("A:G").AutoFit()
            sheet.Activate()
            workbook.Application.ActiveWindow.SplitRow = 1
            workbook.Application.ActiveWindow.FreezePanes = True

        summary.Activate()
        workbook.Save()
