from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TypeAlias

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


StrikeExpiry: TypeAlias = int | tuple[int, str]


def strike_sheet_name(key: StrikeExpiry) -> str:
    if isinstance(key, tuple):
        return f"{key[0]}_{key[1]}"[:31]
    return str(key)


def build_summary_metrics(rows_by_strike: dict[StrikeExpiry, list[dict]]) -> dict[str, float | int | str]:
    latest_rows = []
    for key, rows in rows_by_strike.items():
        if rows:
            latest_row = rows[-1]
            strike = key[0] if isinstance(key, tuple) else key
            latest_row = {"strike": strike, **latest_row}
            latest_rows.append(latest_row)

    if not latest_rows:
        return {
            "total_call_oi": 0,
            "total_put_oi": 0,
            "overall_pcr": 0.0,
            "highest_call_oi_strike": "N/A",
            "highest_put_oi_strike": "N/A",
            "max_pain": "N/A",
        }

    total_call_oi = int(sum(int(row.get("call_oi") or 0) for row in latest_rows))
    total_put_oi = int(sum(int(row.get("put_oi") or 0) for row in latest_rows))
    overall_pcr = (total_put_oi / total_call_oi) if total_call_oi else 0.0

    highest_call_row = max(latest_rows, key=lambda row: int(row.get("call_oi") or 0))
    highest_put_row = max(latest_rows, key=lambda row: int(row.get("put_oi") or 0))

    strikes = sorted({int(row.get("strike") or 0) for row in latest_rows})
    max_pain = "N/A"
    if len(strikes) > 1:
        max_pain = strikes[len(strikes) // 2]

    return {
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "overall_pcr": overall_pcr,
        "highest_call_oi_strike": int(highest_call_row.get("strike") or 0),
        "highest_put_oi_strike": int(highest_put_row.get("strike") or 0),
        "max_pain": max_pain,
    }


def write_daily_workbook(
    output_dir: str | Path,
    symbol: str,
    rows_by_strike: dict[StrikeExpiry, list[dict]],
    trade_date: datetime | None = None,
) -> str:
    if trade_date is None:
        trade_date = datetime.now()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    file_path = output_path / f"OptionChain_{symbol}_{trade_date.strftime('%Y-%m-%d')}.xlsx"

    wb = Workbook()
    header_font = Font(bold=True, color="1F2937")
    header_fill = PatternFill("solid", fgColor="E2E8F0")
    title_fill = PatternFill("solid", fgColor="DDEAFB")
    table_border = Border(
        left=Side(style="thin", color="D0D7DE"),
        right=Side(style="thin", color="D0D7DE"),
        top=Side(style="thin", color="D0D7DE"),
        bottom=Side(style="thin", color="D0D7DE"),
    )

    summary_sheet = wb.active
    summary_sheet.title = "Summary"
    summary_sheet.sheet_view.showGridLines = True
    summary_sheet.append(["Metric", "Value"])
    summary_metrics = build_summary_metrics(rows_by_strike)
    for key, value in summary_metrics.items():
        summary_sheet.append([key, value])
    for cell in summary_sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = table_border
    for row in summary_sheet.iter_rows(min_row=2, max_row=summary_sheet.max_row, min_col=1, max_col=2):
        for cell in row:
            cell.alignment = Alignment(horizontal="left")
            cell.border = table_border
    summary_sheet.freeze_panes = "A2"
    summary_sheet.column_dimensions["A"].width = 28
    summary_sheet.column_dimensions["B"].width = 16
    summary_sheet.auto_filter.ref = summary_sheet.dimensions

    for strike_key, rows in rows_by_strike.items():
        sheet = wb.create_sheet(strike_sheet_name(strike_key))
        sheet.sheet_view.showGridLines = True
        headers = [
            "Time",
            "Strike",
            "Call OI",
            "Call Change in OI",
            "Put OI",
            "Put Change in OI",
        ]
        if isinstance(strike_key, tuple):
            headers.append("Expiry")
        sheet.append(headers)
        for row in rows:
            values = [
                row.get("time_slot"),
                row.get("strike"),
                row.get("call_oi"),
                row.get("call_change_oi"),
                row.get("put_oi"),
                row.get("put_change_oi"),
            ]
            if isinstance(strike_key, tuple):
                values.append(row.get("expiry", strike_key[1]))
            sheet.append(values)
        for cell in sheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = table_border
        column_count = len(headers)
        for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=column_count):
            for cell in row:
                cell.alignment = Alignment(horizontal="center")
                cell.border = table_border
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for col in sheet.columns:
            values = [cell.value for cell in col if cell.value is not None]
            if not values:
                continue
            max_len = max(len(str(value)) for value in values)
            sheet.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 2, 22)

    for sheet in wb.worksheets:
        if sheet.title == "Summary":
            continue
        column_count = sheet.max_column
        for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, min_col=1, max_col=column_count):
            for cell in row:
                if cell.row == 1:
                    cell.fill = title_fill
                else:
                    cell.fill = PatternFill("solid", fgColor="FFFFFF")
                cell.border = table_border

    try:
        wb.save(file_path)
    except PermissionError:
        backup_path = output_path / f"OptionChain_{symbol}_{trade_date.strftime('%Y-%m-%d')}_locked.xlsx"
        wb.save(backup_path)
        return str(backup_path)
    return str(file_path)
