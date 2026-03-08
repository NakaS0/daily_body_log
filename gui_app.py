#!/usr/bin/env python3
"""Tkinter GUI for Daily Body Log (dashboard style)."""
from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from app import DATE_FMT, Record, load_records, parse_optional_positive_float, write_records


class DailyBodyLogGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Daily Body Log")
        self.root.geometry("1400x820")
        self.root.minsize(1180, 640)
        self.root.configure(bg="#eef1f4")

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        self.month_label_var = tk.StringVar()
        self.status_var = tk.StringVar(value="")
        self.card_date_var = tk.StringVar()

        self.rows: dict[str, dict[str, tk.Entry]] = {}

        self._build_layout()
        self.refresh_month()

    def _build_layout(self) -> None:
        shell = tk.Frame(self.root, bg="#eef1f4")
        shell.pack(fill="both", expand=True, padx=12, pady=12)

        self._build_sidebar(shell)
        self._build_content(shell)

    def _build_sidebar(self, parent: tk.Widget) -> None:
        sidebar = tk.Frame(parent, bg="#1f2f2d", width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="BodyLog",
            bg="#1f2f2d",
            fg="#ffffff",
            font=("Yu Gothic UI", 22, "bold"),
            pady=28,
        ).pack(anchor="w", padx=20)

        tk.Label(
            sidebar,
            text="ダッシュボード",
            bg="#8bc34a",
            fg="#103114",
            font=("Yu Gothic UI", 12, "bold"),
            padx=14,
            pady=10,
        ).pack(fill="x", padx=14)

        tk.Label(
            sidebar,
            text="食事・体重・内臓脂肪・運動・履行を\n日単位で記録",
            justify="left",
            bg="#1f2f2d",
            fg="#b5c6c3",
            font=("Yu Gothic UI", 10),
            pady=18,
        ).pack(anchor="w", padx=20)

    def _build_content(self, parent: tk.Widget) -> None:
        content = tk.Frame(parent, bg="#eef1f4")
        content.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self._build_topbar(content)
        self._build_hero_card(content)
        self._build_table_card(content)

    def _build_topbar(self, parent: tk.Widget) -> None:
        topbar = tk.Frame(parent, bg="#ffffff", height=64, bd=1, relief="solid")
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        left = tk.Frame(topbar, bg="#ffffff")
        left.pack(side="left", fill="y", padx=14)

        ttk.Button(left, text="<< 前月", command=self.prev_month).pack(side="left", pady=14)
        ttk.Button(left, text="当月", command=self.go_to_today_month).pack(side="left", padx=8, pady=14)
        ttk.Button(left, text="翌月 >>", command=self.next_month).pack(side="left", pady=14)

        tk.Label(
            left,
            textvariable=self.month_label_var,
            bg="#ffffff",
            fg="#1d2a2f",
            font=("Yu Gothic UI", 13, "bold"),
            padx=16,
        ).pack(side="left")

        tk.Label(
            topbar,
            textvariable=self.status_var,
            bg="#ffffff",
            fg="#3e7c3b",
            font=("Yu Gothic UI", 10, "bold"),
        ).pack(side="right", padx=16)

    def _build_hero_card(self, parent: tk.Widget) -> None:
        hero = tk.Frame(parent, bg="#8bc34a", height=138, bd=0)
        hero.pack(fill="x", pady=(12, 12))
        hero.pack_propagate(False)

        tk.Label(
            hero,
            text="DAILY BODY RECORD",
            bg="#8bc34a",
            fg="#f2ffe8",
            font=("Consolas", 12, "bold"),
        ).pack(anchor="nw", padx=20, pady=(18, 4))

        tk.Label(
            hero,
            textvariable=self.card_date_var,
            bg="#8bc34a",
            fg="#ffffff",
            font=("Yu Gothic UI", 22, "bold"),
        ).pack(anchor="nw", padx=20)

    def _build_table_card(self, parent: tk.Widget) -> None:
        card = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid")
        card.pack(fill="both", expand=True)

        title = tk.Frame(card, bg="#ffffff", height=52)
        title.pack(fill="x")
        title.pack_propagate(False)

        tk.Label(
            title,
            text="1日ごとの記録（セルを直接編集 / Enterまたは移動で自動保存）",
            bg="#ffffff",
            fg="#23313a",
            font=("Yu Gothic UI", 11, "bold"),
        ).pack(anchor="w", padx=14, pady=14)

        outer = tk.Frame(card, bg="#ffffff")
        outer.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(outer, highlightthickness=0, bg="#ffffff")
        y_scroll = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        x_scroll = ttk.Scrollbar(outer, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        self.grid_frame = tk.Frame(self.canvas, bg="#ffffff")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")

        self.grid_frame.bind("<Configure>", self._on_grid_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_grid_configure(self, _: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _make_header_cell(self, row: int, col: int, text: str, width: int) -> None:
        label = tk.Label(
            self.grid_frame,
            text=text,
            width=width,
            borderwidth=1,
            relief="solid",
            bg="#f0f3f5",
            fg="#33414a",
            anchor="center",
            font=("Yu Gothic UI", 10, "bold"),
            pady=6,
        )
        label.grid(row=row, column=col, sticky="nsew")

    def _make_data_label(self, row: int, col: int, value: str, width: int) -> None:
        label = tk.Label(
            self.grid_frame,
            text=value,
            width=width,
            borderwidth=1,
            relief="solid",
            anchor="center",
            bg="#fafcfd",
            fg="#2a3740",
            font=("Yu Gothic UI", 10),
            pady=5,
        )
        label.grid(row=row, column=col, sticky="nsew")

    def _make_data_entry(self, row: int, col: int, value: str, width: int, date_key: str) -> tk.Entry:
        entry = tk.Entry(
            self.grid_frame,
            width=width,
            borderwidth=1,
            relief="solid",
            bg="#ffffff",
            fg="#1f2b33",
            font=("Yu Gothic UI", 10),
        )
        entry.insert(0, value)
        entry.grid(row=row, column=col, sticky="nsew", ipady=4)

        entry.bind("<Return>", lambda _e, d=date_key: self.commit_row(d))
        entry.bind("<FocusOut>", lambda _e, d=date_key: self.commit_row(d))
        return entry

    def refresh_month(self) -> None:
        self.month_label_var.set(f"{self.current_year}年 {self.current_month:02d}月")
        self.card_date_var.set(f"{self.current_year} / {self.current_month:02d}")
        self.status_var.set("")
        self.rows.clear()

        for child in self.grid_frame.winfo_children():
            child.destroy()

        headers = [
            ("日付", 12),
            ("朝食", 18),
            ("昼食", 18),
            ("夕食", 18),
            ("体重", 9),
            ("内臓脂肪", 9),
            ("運動", 22),
            ("履行", 22),
        ]

        for c, (title, width) in enumerate(headers):
            self._make_header_cell(0, c, title, width)
            self.grid_frame.grid_columnconfigure(c, weight=1 if c in (1, 2, 3, 6, 7) else 0)

        existing = {r.log_date: r for r in load_records()}
        days_in_month = calendar.monthrange(self.current_year, self.current_month)[1]

        for day in range(1, days_in_month + 1):
            d = date(self.current_year, self.current_month, day).strftime(DATE_FMT)
            rec = existing.get(d)
            r = day

            self._make_data_label(r, 0, d, 12)

            breakfast = "" if rec is None else rec.breakfast
            lunch = "" if rec is None else rec.lunch
            dinner = "" if rec is None else rec.dinner
            weight = "" if rec is None or rec.weight_kg is None else f"{rec.weight_kg:.1f}"
            visceral = "" if rec is None or rec.visceral_fat_level is None else f"{rec.visceral_fat_level:.1f}"
            exercise = "" if rec is None else rec.exercise
            execution = "" if rec is None else rec.execution

            self.rows[d] = {
                "breakfast": self._make_data_entry(r, 1, breakfast, 18, d),
                "lunch": self._make_data_entry(r, 2, lunch, 18, d),
                "dinner": self._make_data_entry(r, 3, dinner, 18, d),
                "weight": self._make_data_entry(r, 4, weight, 9, d),
                "visceral": self._make_data_entry(r, 5, visceral, 9, d),
                "exercise": self._make_data_entry(r, 6, exercise, 22, d),
                "execution": self._make_data_entry(r, 7, execution, 22, d),
            }

    def commit_row(self, date_key: str) -> None:
        row = self.rows.get(date_key)
        if row is None:
            return

        try:
            breakfast = row["breakfast"].get().strip()
            lunch = row["lunch"].get().strip()
            dinner = row["dinner"].get().strip()
            weight = parse_optional_positive_float(row["weight"].get(), "体重")
            visceral = parse_optional_positive_float(row["visceral"].get(), "内臓脂肪値")
            exercise = row["exercise"].get().strip()
            execution = row["execution"].get().strip()
        except Exception as exc:
            messagebox.showerror("入力エラー", str(exc))
            return

        existing = load_records()
        remaining = [r for r in existing if r.log_date != date_key]

        has_any = any(
            [
                breakfast,
                lunch,
                dinner,
                weight is not None,
                visceral is not None,
                exercise,
                execution,
            ]
        )

        if has_any:
            remaining.append(
                Record(
                    log_date=date_key,
                    breakfast=breakfast,
                    lunch=lunch,
                    dinner=dinner,
                    weight_kg=weight,
                    visceral_fat_level=visceral,
                    exercise=exercise,
                    execution=execution,
                )
            )

        remaining.sort(key=lambda x: x.log_date)
        write_records(remaining)
        self.status_var.set(f"{date_key} 保存済み")

    def prev_month(self) -> None:
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.refresh_month()

    def next_month(self) -> None:
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.refresh_month()

    def go_to_today_month(self) -> None:
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.refresh_month()


def main() -> None:
    root = tk.Tk()
    DailyBodyLogGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
