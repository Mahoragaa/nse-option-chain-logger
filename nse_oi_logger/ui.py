from __future__ import annotations

import threading
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from tkinter import Button, Canvas, Frame, Label, StringVar, Tk, Toplevel, ttk


@dataclass
class AppSettings:
    symbol: str = "NIFTY"
    expiry: str | None = field(default_factory=lambda: date.today().isoformat())
    strikes: str = ""
    auto_atm: bool = False
    interval_minutes: int = 3


def build_default_settings() -> AppSettings:
    return AppSettings()


class DatePickerPopup:
    def __init__(self, parent, variable: StringVar):
        self.parent = parent
        self.variable = variable
        self.view_date = date.today()
        self.popup = None

    def open(self):
        self.view_date = date.today()
        self.popup = Toplevel(self.parent)
        self.popup.title("Select Expiry")
        self.popup.transient(self.parent)
        self.popup.grab_set()
        self.popup.configure(bg="#F8FAFC")
        self.popup.geometry("300x300")
        self.render_calendar()

    def render_calendar(self):
        if self.popup is None:
            return

        for child in self.popup.winfo_children():
            child.destroy()

        month_year = Label(self.popup, text=self._month_label(), bg="#F8FAFC", fg="#0F172A", font=("Segoe UI", 11, "bold"))
        month_year.grid(row=0, column=0, columnspan=7, sticky="ew", padx=12, pady=(12, 8))

        current_month = date.today().replace(day=1)
        viewed_month = self.view_date.replace(day=1)
        prev = Button(
            self.popup,
            text="◀",
            command=lambda: self._shift_month(-1),
            state="disabled" if viewed_month <= current_month else "normal",
            bg="#E2E8F0",
            fg="#0F172A",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        prev.grid(row=1, column=0, padx=(10, 4), pady=4, sticky="ew")
        next_btn = Button(self.popup, text="▶", command=lambda: self._shift_month(1), bg="#E2E8F0", fg="#0F172A", relief="flat", font=("Segoe UI", 10, "bold"))
        next_btn.grid(row=1, column=6, padx=(4, 10), pady=4, sticky="ew")

        for idx, day_name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            header = Label(self.popup, text=day_name, width=4, bg="#F8FAFC", fg="#475569", font=("Segoe UI", 9, "bold"))
            header.grid(row=2, column=idx, padx=2, pady=2)

        first_weekday, days_in_month = monthrange(self.view_date.year, self.view_date.month)
        first_weekday = (first_weekday + 1) % 7
        day_number = 1
        for row in range(3, 9):
            for col in range(7):
                index = (row - 3) * 7 + col
                if index < first_weekday or day_number > days_in_month:
                    Label(self.popup, text="", width=4, height=2, bg="#F8FAFC").grid(row=row, column=col, padx=2, pady=2)
                    continue
                current_day = date(self.view_date.year, self.view_date.month, day_number)
                selected_dates = {item.strip() for item in self.variable.get().split(",")}
                is_selected = current_day.isoformat() in selected_dates
                is_past = current_day < date.today()
                btn = Button(
                    self.popup,
                    text=str(day_number),
                    width=4,
                    height=1,
                    relief="flat",
                    state="disabled" if is_past else "normal",
                    bg="#FFFFFF" if not is_selected else "#1D4ED8",
                    fg="#0F172A" if not is_selected else "#FFFFFF",
                    activebackground="#93C5FD" if not is_selected else "#1E3A8A",
                    activeforeground="#FFFFFF",
                    font=("Segoe UI", 9, "bold"),
                    command=lambda d=current_day: self._select_date(d),
                )
                btn.grid(row=row, column=col, padx=2, pady=2)
                day_number += 1

        self.popup.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

    def _month_label(self) -> str:
        return self.view_date.strftime("%B %Y")

    def _shift_month(self, delta: int):
        y = self.view_date.year + (self.view_date.month - 1 + delta) // 12
        m = (self.view_date.month - 1 + delta) % 12 + 1
        self.view_date = self.view_date.replace(year=y, month=m, day=1)
        self.render_calendar()

    def _select_date(self, selected: date):
        if selected < date.today():
            return
        selected_values = [value.strip() for value in self.variable.get().split(",") if value.strip()]
        iso_date = selected.isoformat()
        if iso_date not in selected_values:
            selected_values.append(iso_date)
            selected_values.sort()
            self.variable.set(", ".join(selected_values))
        if self.popup is not None:
            self.popup.destroy()
            self.popup = None


class OptionChainApp:
    def __init__(self, run_once_callback=None, schedule_callback=None):
        self.root = Tk()
        self.root.title("NSE Option Chain Logger")
        self.root.geometry("900x570")
        self.root.minsize(760, 470)
        self.root.configure(bg="#F3F5F8")
        self.run_once_callback = run_once_callback
        self.schedule_callback = schedule_callback
        self.status_var = StringVar(value="Ready")

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#F3F5F8")
        style.configure("Card.TFrame", background="#FFFFFF")
        style.configure("Title.TLabel", background="#F3F5F8", foreground="#0F172A", font=("Segoe UI", 16, "bold"))
        style.configure("Field.TLabel", background="#F3F5F8", foreground="#334155", font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", background="#FFFFFF", foreground="#334155", font=("Segoe UI", 9))
        style.configure("TEntry", fieldbackground="#FFFFFF", foreground="#0F172A", font=("Segoe UI", 10), padding=8)
        style.configure("Primary.TButton", background="#1D4ED8", foreground="#FFFFFF", font=("Segoe UI", 10, "bold"), padding=(16, 9))
        style.map("Primary.TButton", background=[("active", "#1E3A8A"), ("pressed", "#1E3A8A")], foreground=[("active", "#FFFFFF")])
        style.configure("Secondary.TButton", background="#E2E8F0", foreground="#0F172A", font=("Segoe UI", 10, "bold"), padding=(16, 9))
        style.map("Secondary.TButton", background=[("active", "#CBD5E1"), ("pressed", "#CBD5E1")])

        container = ttk.Frame(self.root, padding=(22, 18, 22, 18), style="App.TFrame")
        container.pack(fill="both", expand=True)

        card = ttk.Frame(container, padding=(18, 16, 18, 16), style="Card.TFrame")
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="NSE Option Chain Logger", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Separator(card, orient="horizontal").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        self.symbol_var = StringVar(value="NIFTY")
        ttk.Label(card, text="Symbol", style="Field.TLabel").grid(row=2, column=0, padx=(0, 12), pady=8, sticky="w")
        ttk.Entry(card, textvariable=self.symbol_var, width=28).grid(row=2, column=1, sticky="ew")

        ttk.Label(
            card,
            text="Add one row per strike. Enter one or more expiry dates for each strike.",
            style="Field.TLabel",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 6))

        selections = Frame(card, bg="#FFFFFF", bd=1, relief="solid")
        selections.grid(row=4, column=0, columnspan=2, sticky="nsew")
        self.selection_canvas = Canvas(selections, height=205, highlightthickness=0, bg="#FFFFFF")
        scrollbar = ttk.Scrollbar(selections, orient="vertical", command=self.selection_canvas.yview)
        self.selection_canvas.configure(yscrollcommand=scrollbar.set)
        self.selection_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        selections.rowconfigure(0, weight=1)
        selections.columnconfigure(0, weight=1)
        self.rows_frame = ttk.Frame(self.selection_canvas)
        self.rows_window = self.selection_canvas.create_window(
            (0, 0),
            window=self.rows_frame,
            anchor="nw",
        )
        self.rows_frame.bind(
            "<Configure>",
            lambda event: self.selection_canvas.configure(
                scrollregion=(0, 0, event.width, event.height)
            ),
        )
        self.selection_canvas.bind(
            "<Configure>",
            lambda event: self.selection_canvas.itemconfigure(
                self.rows_window,
                width=event.width,
            ),
        )
        self.selection_rows: list[tuple[StringVar, StringVar]] = []
        self._add_selection_row()
        ttk.Button(card, text="Add strike", command=self._add_selection_row).grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )

        self.run_button = Button(
            card,
            text="Run once",
            command=self._run_once,
            bg="#1D4ED8",
            fg="#FFFFFF",
            activebackground="#1E3A8A",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=16,
            pady=8,
            font=("Segoe UI", 10, "bold"),
        )
        self.run_button.grid(row=6, column=0, padx=(0, 8), pady=(14, 0), sticky="ew")

        self.schedule_button = Button(
            card,
            text="Start schedule",
            command=self._schedule,
            bg="#E2E8F0",
            fg="#0F172A",
            activebackground="#CBD5E1",
            activeforeground="#0F172A",
            relief="flat",
            padx=16,
            pady=8,
            font=("Segoe UI", 10, "bold"),
        )
        self.schedule_button.grid(row=6, column=1, pady=(14, 0), sticky="ew")

        self.stop_button = Button(
            card,
            text="Stop schedule",
            command=self._stop_schedule,
            bg="#FEE2E2",
            fg="#991B1B",
            activebackground="#FECACA",
            activeforeground="#7F1D1D",
            relief="flat",
            padx=16,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            state="disabled",
        )
        self.stop_button.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        ttk.Label(
            card,
            textvariable=self.status_var,
            style="Status.TLabel",
            wraplength=820,
            justify="left",
        ).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        card.columnconfigure(1, weight=1)
        card.rowconfigure(4, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self._schedule_stop_event: threading.Event | None = None

    def _add_selection_row(self):
        self.selection_rows.append((StringVar(), StringVar()))
        self._render_selection_rows()

    def _remove_selection_row(self, index: int):
        if len(self.selection_rows) == 1:
            self.selection_rows[0][0].set("")
            self.selection_rows[0][1].set("")
        else:
            self.selection_rows.pop(index)
        self._render_selection_rows()

    def _render_selection_rows(self):
        for child in self.rows_frame.winfo_children():
            child.destroy()

        for column, text in enumerate(
            ("Strike", "Expiry dates (YYYY-MM-DD, comma-separated)", "", "")
        ):
            ttk.Label(self.rows_frame, text=text).grid(
                row=0,
                column=column,
                sticky="w",
                padx=6,
                pady=5,
            )

        for index, (strike_var, expiry_var) in enumerate(self.selection_rows, start=1):
            ttk.Entry(self.rows_frame, textvariable=strike_var, width=14).grid(
                row=index,
                column=0,
                sticky="ew",
                padx=6,
                pady=4,
            )
            ttk.Entry(self.rows_frame, textvariable=expiry_var).grid(
                row=index,
                column=1,
                sticky="ew",
                padx=6,
                pady=4,
            )
            Button(
                self.rows_frame,
                text="📅",
                command=lambda variable=expiry_var: DatePickerPopup(self.root, variable).open(),
                bg="#F1F5F9",
                fg="#0F172A",
                relief="flat",
                padx=8,
            ).grid(row=index, column=2, padx=3, pady=4)
            ttk.Button(
                self.rows_frame,
                text="Remove",
                command=lambda row=index - 1: self._remove_selection_row(row),
            ).grid(row=index, column=3, padx=6, pady=4)
        self.rows_frame.columnconfigure(1, weight=1)

    def _run_once(self):
        self._start_action(
            self.run_once_callback,
            self.run_button,
            "Running one cycle...",
            selection_entries=self._selection_entries(),
        )

    def _schedule(self):
        self._schedule_stop_event = threading.Event()
        self.run_button.configure(state="disabled")
        self._start_action(
            self.schedule_callback,
            self.schedule_button,
            "Starting scheduled logging...",
            on_status=self._schedule_status,
            selection_entries=self._selection_entries(),
            stop_event=self._schedule_stop_event,
        )

    def _stop_schedule(self):
        if self._schedule_stop_event is None:
            self.status_var.set("No schedule is currently running.")
            return
        self.stop_button.configure(state="disabled")
        self.status_var.set("Stopping schedule...")
        self._schedule_stop_event.set()

    def _schedule_status(self, status: str):
        self.root.after(0, self._set_schedule_status, status)

    def _set_schedule_status(self, status: str):
        self.status_var.set(status)
        if status.startswith("Schedule started"):
            self.stop_button.configure(state="normal")

    def _selection_entries(self) -> list[tuple[str, str]]:
        return [
            (strike_var.get(), expiry_var.get())
            for strike_var, expiry_var in self.selection_rows
        ]

    def _start_action(self, callback, button, starting_status: str, **extra_params):
        if callback is None:
            self.status_var.set("This action is not available.")
            return

        button.configure(state="disabled")
        self.status_var.set(starting_status)
        params = {
            "symbol": self.symbol_var.get().strip(),
            **extra_params,
        }
        thread = threading.Thread(
            target=self._run_callback,
            args=(callback, params, button),
            daemon=True,
        )
        thread.start()

    def _run_callback(self, callback, params, button):
        try:
            result = callback(**params)
            status = str(result) if result else "Completed."
        except Exception as exc:
            status = f"Failed: {exc}"
        self.root.after(0, self._finish_action, button, status)

    def _finish_action(self, button, status: str):
        button.configure(state="normal")
        if button is self.schedule_button:
            self.run_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self._schedule_stop_event = None
        self.status_var.set(status)

    def _report_status(self, status: str):
        self.root.after(0, self.status_var.set, status)

    def start(self):
        self.root.mainloop()
