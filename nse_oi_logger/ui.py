from __future__ import annotations

import threading
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from tkinter import Button, Entry, Frame, Label, StringVar, Tk, Toplevel, ttk


@dataclass
class AppSettings:
    symbol: str = "NIFTY"
    expiry: str | None = "2026-10-28"
    strikes: str = "24500,24600,24700"
    auto_atm: bool = False
    interval_minutes: int = 3


def build_default_settings() -> AppSettings:
    return AppSettings()


class DatePickerPopup:
    def __init__(self, parent, variable: StringVar):
        self.parent = parent
        self.variable = variable
        self.view_date = datetime.strptime(variable.get() or date.today().isoformat(), "%Y-%m-%d").date()
        self.popup = None

    def open(self):
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

        prev = Button(self.popup, text="◀", command=lambda: self._shift_month(-1), bg="#E2E8F0", fg="#0F172A", relief="flat", font=("Segoe UI", 10, "bold"))
        prev.grid(row=1, column=0, padx=(10, 4), pady=4, sticky="ew")
        next_btn = Button(self.popup, text="▶", command=lambda: self._shift_month(1), bg="#E2E8F0", fg="#0F172A", relief="flat", font=("Segoe UI", 10, "bold"))
        next_btn.grid(row=1, column=6, padx=(4, 10), pady=4, sticky="ew")

        for idx, day_name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            header = Label(self.popup, text=day_name, width=4, bg="#F8FAFC", fg="#475569", font=("Segoe UI", 9, "bold"))
            header.grid(row=2, column=idx, padx=2, pady=2)

        first_weekday, days_in_month = monthrange(self.view_date.year, self.view_date.month)
        day_number = 1
        for row in range(3, 9):
            for col in range(7):
                index = (row - 3) * 7 + col
                if index < first_weekday or day_number > days_in_month:
                    Label(self.popup, text="", width=4, height=2, bg="#F8FAFC").grid(row=row, column=col, padx=2, pady=2)
                    continue
                current_day = date(self.view_date.year, self.view_date.month, day_number)
                is_selected = current_day.isoformat() == self.variable.get()
                btn = Button(
                    self.popup,
                    text=str(day_number),
                    width=4,
                    height=1,
                    relief="flat",
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
        self.view_date = self.view_date.replace(year=y, month=m)
        self.render_calendar()

    def _select_date(self, selected: date):
        self.variable.set(selected.isoformat())
        if self.popup is not None:
            self.popup.destroy()
            self.popup = None


class OptionChainApp:
    def __init__(self, run_once_callback=None, schedule_callback=None):
        self.root = Tk()
        self.root.title("NSE Option Chain Logger")
        self.root.geometry("480x320")
        self.root.minsize(430, 280)
        self.root.configure(bg="#F3F5F8")
        self.run_once_callback = run_once_callback
        self.schedule_callback = schedule_callback

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#F3F5F8")
        style.configure("Card.TFrame", background="#FFFFFF")
        style.configure("Title.TLabel", background="#F3F5F8", foreground="#0F172A", font=("Segoe UI", 16, "bold"))
        style.configure("Field.TLabel", background="#F3F5F8", foreground="#334155", font=("Segoe UI", 10, "bold"))
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
        self.expiry_var = StringVar(value="2026-10-28")
        self.strikes_var = StringVar(value="24500,24600,24700")

        ttk.Label(card, text="Symbol", style="Field.TLabel").grid(row=2, column=0, padx=(0, 12), pady=8, sticky="w")
        ttk.Entry(card, textvariable=self.symbol_var, width=28).grid(row=2, column=1, padx=(0, 0), pady=8, sticky="ew")

        ttk.Label(card, text="Expiry", style="Field.TLabel").grid(row=3, column=0, padx=(0, 12), pady=8, sticky="w")
        expiry_frame = Frame(card, bg="#FFFFFF", bd=1, relief="solid")
        expiry_frame.grid(row=3, column=1, pady=8, sticky="ew")
        Entry(expiry_frame, textvariable=self.expiry_var, width=24, bd=0, highlightthickness=0, font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, padx=(8, 0), pady=5)
        Button(expiry_frame, text="📅", command=lambda: DatePickerPopup(self.root, self.expiry_var).open(), bg="#F1F5F9", fg="#0F172A", relief="flat", padx=10, pady=4, font=("Segoe UI", 10, "bold")).pack(side="right", fill="y", padx=(8, 8))

        ttk.Label(card, text="Strikes", style="Field.TLabel").grid(row=4, column=0, padx=(0, 12), pady=8, sticky="w")
        ttk.Entry(card, textvariable=self.strikes_var, width=28).grid(row=4, column=1, pady=8, sticky="ew")

        Button(
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
        ).grid(row=5, column=0, padx=(0, 8), pady=(18, 0), sticky="ew")

        Button(
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
        ).grid(row=5, column=1, pady=(18, 0), sticky="ew")

        card.columnconfigure(1, weight=1)
        card.rowconfigure(5, weight=1)
        self.root.columnconfigure(0, weight=1)

    def _run_once(self):
        if self.run_once_callback:
            params = {
                "symbol": self.symbol_var.get(),
                "expiry": self.expiry_var.get() or None,
                "strikes": self.strikes_var.get(),
            }
            thread = threading.Thread(target=self.run_once_callback, kwargs=params, daemon=True)
            thread.start()

    def _schedule(self):
        if self.schedule_callback:
            params = {
                "symbol": self.symbol_var.get(),
                "expiry": self.expiry_var.get() or None,
                "strikes": self.strikes_var.get(),
            }
            thread = threading.Thread(target=self.schedule_callback, kwargs=params, daemon=True)
            thread.start()

    def start(self):
        self.root.mainloop()
