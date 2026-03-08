#!/usr/bin/env python3
"""Daily body log CLI app.

Records breakfast/lunch/dinner meals, weight, and visceral fat level.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "records.csv"
DATE_FMT = "%Y-%m-%d"


@dataclass
class Record:
    log_date: str
    breakfast: str
    lunch: str
    dinner: str
    weight_kg: float | None
    visceral_fat_level: float | None
    exercise: str = ""
    execution: str = ""

    def to_row(self) -> list[str]:
        return [
            self.log_date,
            self.breakfast,
            self.lunch,
            self.dinner,
            "" if self.weight_kg is None else f"{self.weight_kg:.1f}",
            "" if self.visceral_fat_level is None else f"{self.visceral_fat_level:.1f}",
            self.exercise,
            self.execution,
        ]


def ensure_data_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        with DATA_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "date",
                    "breakfast",
                    "lunch",
                    "dinner",
                    "weight_kg",
                    "visceral_fat_level",
                    "exercise",
                    "execution",
                ]
            )


def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, DATE_FMT)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"日付形式が不正です: {value} (例: 2026-03-08)"
        ) from exc
    return value


def parse_positive_float(value: str, field_name: str) -> float:
    try:
        f = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{field_name}は数値で入力してください") from exc
    if f <= 0:
        raise argparse.ArgumentTypeError(f"{field_name}は0より大きい値で入力してください")
    return f


def parse_optional_positive_float(value: str, field_name: str) -> float | None:
    v = value.strip()
    if not v:
        return None
    return parse_positive_float(v, field_name)


def load_records() -> list[Record]:
    ensure_data_file()
    rows: list[Record] = []
    with DATA_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                Record(
                    log_date=row["date"],
                    breakfast=row["breakfast"],
                    lunch=row["lunch"],
                    dinner=row["dinner"],
                    weight_kg=float(row["weight_kg"]) if row.get("weight_kg", "").strip() else None,
                    visceral_fat_level=(
                        float(row["visceral_fat_level"])
                        if row.get("visceral_fat_level", "").strip()
                        else None
                    ),
                    exercise=row.get("exercise", ""),
                    execution=row.get("execution", ""),
                )
            )
    return rows


def save_record(record: Record) -> None:
    ensure_data_file()
    with DATA_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(record.to_row())


def write_records(records: list[Record]) -> None:
    ensure_data_file()
    with DATA_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "date",
                "breakfast",
                "lunch",
                "dinner",
                "weight_kg",
                "visceral_fat_level",
                "exercise",
                "execution",
            ]
        )
        for record in records:
            writer.writerow(record.to_row())


def upsert_record(record: Record) -> None:
    records = load_records()
    for i, existing in enumerate(records):
        if existing.log_date == record.log_date:
            records[i] = record
            write_records(records)
            return
    records.append(record)
    write_records(records)


def print_table(records: Iterable[Record]) -> None:
    records = list(records)
    if not records:
        print("記録がありません。")
        return

    headers = ["日付", "朝", "昼", "晩", "体重(kg)", "内臓脂肪"]
    rows = [
        [
            r.log_date,
            r.breakfast,
            r.lunch,
            r.dinner,
            "" if r.weight_kg is None else f"{r.weight_kg:.1f}",
            "" if r.visceral_fat_level is None else f"{r.visceral_fat_level:.1f}",
        ]
        for r in records
    ]

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def format_row(cols: list[str]) -> str:
        return " | ".join(col.ljust(widths[i]) for i, col in enumerate(cols))

    print(format_row(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(format_row(row))


def add_command(args: argparse.Namespace) -> None:
    log_date = args.date or date.today().strftime(DATE_FMT)
    record = Record(
        log_date=validate_date(log_date),
        breakfast=args.breakfast,
        lunch=args.lunch,
        dinner=args.dinner,
        weight_kg=parse_positive_float(str(args.weight), "体重"),
        visceral_fat_level=parse_positive_float(str(args.visceral_fat), "内臓脂肪値"),
        exercise=args.exercise or "",
        execution=args.execution or "",
    )
    upsert_record(record)
    print(f"記録を保存しました: {record.log_date}")


def list_command(args: argparse.Namespace) -> None:
    records = load_records()
    records.sort(key=lambda r: r.log_date, reverse=True)
    if args.limit:
        records = records[: args.limit]
    print_table(records)


def today_command(_: argparse.Namespace) -> None:
    today = date.today().strftime(DATE_FMT)
    records = [r for r in load_records() if r.log_date == today]
    print_table(records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="食事・体重・内臓脂肪値を記録する日次ログアプリ"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="記録を追加")
    add_parser.add_argument("--date", type=validate_date, help="記録日 (YYYY-MM-DD)")
    add_parser.add_argument("--breakfast", required=True, help="朝食")
    add_parser.add_argument("--lunch", required=True, help="昼食")
    add_parser.add_argument("--dinner", required=True, help="夕食")
    add_parser.add_argument("--weight", required=True, type=float, help="体重(kg)")
    add_parser.add_argument(
        "--visceral-fat", required=True, type=float, help="内臓脂肪値"
    )
    add_parser.add_argument("--exercise", default="", help="運動")
    add_parser.add_argument("--execution", default="", help="履行")
    add_parser.set_defaults(func=add_command)

    list_parser = sub.add_parser("list", help="記録を一覧表示")
    list_parser.add_argument("--limit", type=int, default=0, help="表示件数")
    list_parser.set_defaults(func=list_command)

    today_parser = sub.add_parser("today", help="今日の記録を表示")
    today_parser.set_defaults(func=today_command)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
