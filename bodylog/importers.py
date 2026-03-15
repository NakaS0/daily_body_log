"""Import and export helpers for DailyRecord data."""

import csv
import json
import shutil
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import BinaryIO, TextIO

from django.core import serializers

from .models import DailyRecord

DATE_COLUMN_CANDIDATES = [
    "date",
    "day",
    "datetime",
    "timestamp",
    "measured date",
    "measurement date",
    "measured at",
    "計測日",
    "測定日",
    "測定日時",
    "日付",
    "日時",
]

WEIGHT_COLUMN_CANDIDATES = [
    "weight",
    "weight(kg)",
    "weight kg",
    "body weight",
    "体重",
]

VISCERAL_COLUMN_CANDIDATES = [
    "body fat",
    "body fat percentage",
    "body fat %",
    "body fat percent",
    "fat %",
    "fat percent",
    "体脂肪(%)",
    "体脂肪率",
    "体脂肪率(%)",
    "体脂肪率％",
    "体脂肪",
    # Backward-compatible fallbacks for older CSV exports.
    "visceral fat",
    "visceral fat level",
    "visceral fat percentage",
    "visceral fat %",
    "内臓脂肪",
    "内臓脂肪レベル",
    "内臓脂肪率",
]

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
]


def _normalize_header(value: str) -> str:
    normalized = value.strip().lower().replace("_", " ")
    normalized = normalized.replace("（", "(").replace("）", ")")
    return " ".join(normalized.split())


def _find_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    normalized_fields = {_normalize_header(name): name for name in fieldnames}
    for candidate in candidates:
        match = normalized_fields.get(_normalize_header(candidate))
        if match:
            return match
    for candidate in candidates:
        normalized_candidate = _normalize_header(candidate)
        for normalized_field, original_field in normalized_fields.items():
            if normalized_candidate in normalized_field:
                return original_field
    return None


def _has_supported_columns(fieldnames: list[str]) -> bool:
    date_column = _find_column(fieldnames, DATE_COLUMN_CANDIDATES)
    weight_column = _find_column(fieldnames, WEIGHT_COLUMN_CANDIDATES)
    visceral_column = _find_column(fieldnames, VISCERAL_COLUMN_CANDIDATES)
    return bool(date_column and (weight_column or visceral_column))


def _build_reader_from_lines(lines: list[str]) -> csv.DictReader:
    if not lines:
        raise ValueError("CSV does not have headers")

    search_limit = min(len(lines), 10)
    for start_index in range(search_limit):
        reader = csv.DictReader(lines[start_index:])
        fieldnames = reader.fieldnames or []
        if _has_supported_columns(fieldnames):
            return reader

    reader = csv.DictReader(lines)
    if not (reader.fieldnames or []):
        raise ValueError("CSV does not have headers")
    return reader


def _parse_date(raw_value: str) -> date:
    value = raw_value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date: {raw_value}")


def _parse_decimal(raw_value: str) -> Decimal | None:
    value = raw_value.strip()
    if not value:
        return None
    normalized = value.replace(",", "")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Could not parse number: {raw_value}") from exc
    if parsed <= 0:
        return None
    return parsed.quantize(Decimal("0.1"))


def _open_csv_text(path: Path) -> TextIO:
    try:
        return path.open("r", newline="", encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.open("r", newline="", encoding="cp932")


def _decode_uploaded_csv(uploaded_file: BinaryIO) -> str:
    raw = uploaded_file.read()
    for encoding in ("utf-8-sig", "cp932", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not determine CSV encoding")


def _import_reader(reader: csv.DictReader) -> int:
    fieldnames = reader.fieldnames or []
    if not fieldnames:
        raise ValueError("CSV does not have headers")

    date_column = _find_column(fieldnames, DATE_COLUMN_CANDIDATES)
    weight_column = _find_column(fieldnames, WEIGHT_COLUMN_CANDIDATES)
    visceral_column = _find_column(fieldnames, VISCERAL_COLUMN_CANDIDATES)

    if not date_column:
        raise ValueError("Could not find a date column in CSV")
    if not weight_column and not visceral_column:
        raise ValueError("Could not find weight or body fat percentage columns in CSV")

    # For duplicate dates in a CSV, keep the row with the lowest weight.
    selected_rows: dict[date, tuple[Decimal | None, Decimal | None]] = {}
    for row in reader:
        raw_date = (row.get(date_column) or "").strip()
        if not raw_date:
            continue

        log_date = _parse_date(raw_date)
        weight_value = _parse_decimal(row.get(weight_column, "")) if weight_column else None
        visceral_value = _parse_decimal(row.get(visceral_column, "")) if visceral_column else None

        if weight_value is None and visceral_value is None:
            continue

        current = selected_rows.get(log_date)
        if current is None:
            selected_rows[log_date] = (weight_value, visceral_value)
            continue

        current_weight, current_visceral = current
        if weight_value is None:
            if current_weight is None and visceral_value is not None:
                selected_rows[log_date] = (current_weight, visceral_value)
            continue

        if current_weight is None or weight_value < current_weight:
            selected_rows[log_date] = (weight_value, visceral_value)
            continue

        if weight_value == current_weight and current_visceral is None and visceral_value is not None:
            selected_rows[log_date] = (weight_value, visceral_value)

    imported_count = 0
    for log_date, (weight_value, visceral_value) in selected_rows.items():
        record, _ = DailyRecord.objects.get_or_create(log_date=log_date)
        if weight_value is not None:
            record.weight_kg = weight_value
        if visceral_value is not None:
            record.visceral_fat_level = visceral_value
        record.save()
        imported_count += 1

    return imported_count


def import_csv_records(csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    with _open_csv_text(csv_path) as handle:
        reader = _build_reader_from_lines(handle.read().splitlines())
        return _import_reader(reader)


def import_uploaded_csv(uploaded_file: BinaryIO) -> int:
    decoded = _decode_uploaded_csv(uploaded_file)
    reader = _build_reader_from_lines(decoded.splitlines())
    return _import_reader(reader)


def _parse_fixture_decimal(raw_value: str | None) -> Decimal | None:
    if raw_value in (None, ""):
        return None
    try:
        return Decimal(str(raw_value)).quantize(Decimal("0.1"))
    except InvalidOperation as exc:
        raise ValueError(f"Could not parse fixture number: {raw_value}") from exc


def import_json_fixture(json_path: Path) -> int:
    if not json_path.exists():
        return 0

    raw = json_path.read_bytes()
    payload = None
    for encoding in ("utf-8-sig", "cp932", "utf-8"):
        try:
            payload = json.loads(raw.decode(encoding))
            break
        except UnicodeDecodeError:
            continue

    if payload is None:
        raise ValueError("Could not determine JSON fixture encoding")
    if not isinstance(payload, list):
        raise ValueError("JSON fixture must be a list")

    imported_count = 0
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each JSON fixture entry must be an object")
        if item.get("model") != "bodylog.dailyrecord":
            continue

        fields = item.get("fields")
        if not isinstance(fields, dict):
            raise ValueError("Invalid fields in JSON fixture")

        raw_date = fields.get("log_date")
        if not raw_date:
            raise ValueError("JSON fixture entry is missing log_date")

        try:
            log_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"Invalid log_date: {raw_date}") from exc

        record, _ = DailyRecord.objects.get_or_create(log_date=log_date)
        record.breakfast = str(fields.get("breakfast", ""))
        record.lunch = str(fields.get("lunch", ""))
        record.dinner = str(fields.get("dinner", ""))
        record.weight_kg = _parse_fixture_decimal(fields.get("weight_kg"))
        record.visceral_fat_level = _parse_fixture_decimal(fields.get("visceral_fat_level"))
        record.exercise = str(fields.get("exercise", ""))
        record.execution = str(fields.get("execution", ""))
        record.replacement_achieved = bool(fields.get("replacement_achieved", False))
        record.save()
        imported_count += 1

    return imported_count


def export_json_fixture(json_path: Path) -> int:
    records = DailyRecord.objects.order_by("log_date")
    payload = serializers.serialize("json", records, ensure_ascii=False, indent=2)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(payload, encoding="utf-8")
    return records.count()


def move_processed_file(source_path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = target_dir / f"{source_path.stem}_{timestamp}{source_path.suffix}"
    counter = 1
    while destination.exists():
        destination = target_dir / f"{source_path.stem}_{timestamp}_{counter}{source_path.suffix}"
        counter += 1
    shutil.move(str(source_path), str(destination))
    return destination
