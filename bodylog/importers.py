import csv
import shutil
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import BinaryIO, TextIO

from .models import DailyRecord

DATE_COLUMN_CANDIDATES = [
    "date",
    "measurement date",
    "measured at",
    "測定日",
    "日付",
    "日時",
]

WEIGHT_COLUMN_CANDIDATES = [
    "weight",
    "weight(kg)",
    "body weight",
    "体重",
]

VISCERAL_COLUMN_CANDIDATES = [
    "visceral fat",
    "visceral fat level",
    "visceral fat percentage",
    "内臓脂肪",
    "内臓脂肪レベル",
    "内臓脂肪値",
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
    return " ".join(value.strip().lower().replace("_", " ").split())


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


def _parse_date(raw_value: str) -> datetime.date:
    value = raw_value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"日付を解釈できません: {raw_value}")


def _parse_decimal(raw_value: str) -> Decimal | None:
    value = raw_value.strip()
    if not value:
        return None
    normalized = value.replace(",", "")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"数値を解釈できません: {raw_value}") from exc
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
    raise ValueError("CSV の文字コードを判定できませんでした")


def _import_reader(reader: csv.DictReader) -> int:
    fieldnames = reader.fieldnames or []
    if not fieldnames:
        raise ValueError("CSV にヘッダー行がありません")

    date_column = _find_column(fieldnames, DATE_COLUMN_CANDIDATES)
    weight_column = _find_column(fieldnames, WEIGHT_COLUMN_CANDIDATES)
    visceral_column = _find_column(fieldnames, VISCERAL_COLUMN_CANDIDATES)

    if not date_column:
        raise ValueError("日付列を特定できませんでした")
    if not weight_column and not visceral_column:
        raise ValueError("体重列または内臓脂肪列を特定できませんでした")

    imported_count = 0
    for row in reader:
        raw_date = (row.get(date_column) or "").strip()
        if not raw_date:
            continue

        log_date = _parse_date(raw_date)
        weight_value = _parse_decimal(row.get(weight_column, "")) if weight_column else None
        visceral_value = _parse_decimal(row.get(visceral_column, "")) if visceral_column else None

        if weight_value is None and visceral_value is None:
            continue

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
        reader = csv.DictReader(handle)
        return _import_reader(reader)


def import_uploaded_csv(uploaded_file: BinaryIO) -> int:
    decoded = _decode_uploaded_csv(uploaded_file)
    reader = csv.DictReader(decoded.splitlines())
    return _import_reader(reader)


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
