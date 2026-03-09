import calendar
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .importers import import_uploaded_csv
from .models import DailyRecord

BREAKFAST_OPTIONS = [
    "活力＋VM1122",
    "サボリ",
    "不明",
]

LUNCH_OPTIONS = [
    "D24＋推奨食事",
    "D24＋ジュニアバランス1杯",
    "外食",
    "サボリ",
    "不明",
]

DINNER_OPTIONS = [
    "NB",
    "活力＋VM1122",
    "外食",
    "サボリ",
    "不明",
]

MEAL_SEPARATOR = " / "


def _build_exercise_options() -> list[str]:
    options = [""]
    for minutes in range(30, 301, 30):
        hours, rest = divmod(minutes, 60)
        if hours and rest:
            label = f"{hours}時間{rest}分"
        elif hours:
            label = f"{hours}時間"
        else:
            label = f"{rest}分"
        options.append(label)
    return options


EXERCISE_OPTIONS = _build_exercise_options()


def _parse_optional_decimal(raw_value: str, field_label: str) -> Decimal | None:
    value = raw_value.strip()
    if not value:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field_label}は数値で入力してください") from exc
    if parsed <= 0:
        raise ValueError(f"{field_label}は0より大きい値で入力してください")
    return parsed.quantize(Decimal("0.1"))


def _split_multi_value(raw_value: str) -> list[str]:
    if not raw_value.strip():
        return []
    return [item.strip() for item in raw_value.split(MEAL_SEPARATOR) if item.strip()]


def _join_multi_value(values: list[str]) -> str:
    return MEAL_SEPARATOR.join(value.strip() for value in values if value.strip())


def dashboard(request: HttpRequest, year: int | None = None, month: int | None = None) -> HttpResponse:
    today = date.today()
    display_year = year or today.year
    display_month = month or today.month
    if not 1 <= display_month <= 12:
        return redirect("bodylog:dashboard")

    first_day = date(display_year, display_month, 1)
    days_in_month = calendar.monthrange(display_year, display_month)[1]
    month_records = {
        record.log_date: record
        for record in DailyRecord.objects.filter(
            log_date__year=display_year,
            log_date__month=display_month,
        )
    }

    month_days = []
    previous_weight: str = ""
    previous_visceral: str = ""
    for day in range(1, days_in_month + 1):
        current_day = date(display_year, display_month, day)
        record = month_records.get(current_day)
        breakfast_value = record.breakfast if record else ""
        lunch_value = record.lunch if record else ""
        dinner_value = record.dinner if record else ""
        weight_value = ""
        visceral_value = ""
        if record and record.weight_kg is not None:
            weight_value = f"{record.weight_kg:.1f}"
        if record and record.visceral_fat_level is not None:
            visceral_value = f"{record.visceral_fat_level:.1f}"
        month_days.append(
            {
                "date": current_day,
                "record": record,
                "breakfast_value": breakfast_value,
                "lunch_value": lunch_value,
                "dinner_value": dinner_value,
                "breakfast_selected": _split_multi_value(breakfast_value),
                "lunch_selected": _split_multi_value(lunch_value),
                "dinner_selected": _split_multi_value(dinner_value),
                "weight_value": weight_value,
                "visceral_value": visceral_value,
                "weight_placeholder": "" if weight_value else previous_weight,
                "visceral_placeholder": "" if visceral_value else previous_visceral,
            }
        )
        if weight_value:
            previous_weight = weight_value
        if visceral_value:
            previous_visceral = visceral_value

    prev_year, prev_month = (display_year - 1, 12) if display_month == 1 else (display_year, display_month - 1)
    next_year, next_month = (display_year + 1, 1) if display_month == 12 else (display_year, display_month + 1)

    context = {
        "display_year": display_year,
        "display_month": display_month,
        "month_label": first_day.strftime("%Y年 %m月"),
        "month_days": month_days,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "breakfast_options": BREAKFAST_OPTIONS,
        "lunch_options": LUNCH_OPTIONS,
        "dinner_options": DINNER_OPTIONS,
        "exercise_options": EXERCISE_OPTIONS,
    }
    return render(request, "bodylog/dashboard.html", context)


@require_POST
def save_record(request: HttpRequest, date_value: str) -> JsonResponse:
    try:
        log_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        breakfast = _join_multi_value(_split_multi_value(request.POST.get("breakfast", "")))
        lunch = _join_multi_value(_split_multi_value(request.POST.get("lunch", "")))
        dinner = _join_multi_value(_split_multi_value(request.POST.get("dinner", "")))
        weight_kg = _parse_optional_decimal(request.POST.get("weight_kg", ""), "体重")
        visceral_fat_level = _parse_optional_decimal(
            request.POST.get("visceral_fat_level", ""),
            "内臓脂肪値",
        )
        exercise = request.POST.get("exercise", "").strip()
        execution = request.POST.get("execution", "").strip()
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    has_any = any(
        [
            breakfast,
            lunch,
            dinner,
            weight_kg is not None,
            visceral_fat_level is not None,
            exercise,
            execution,
        ]
    )

    if not has_any:
        DailyRecord.objects.filter(log_date=log_date).delete()
        return JsonResponse({"ok": True, "status": "deleted", "date": log_date.isoformat()})

    record, _ = DailyRecord.objects.get_or_create(log_date=log_date)
    record.breakfast = breakfast
    record.lunch = lunch
    record.dinner = dinner
    record.weight_kg = weight_kg
    record.visceral_fat_level = visceral_fat_level
    record.exercise = exercise
    record.execution = execution
    record.save()
    return JsonResponse({"ok": True, "status": "saved", "date": log_date.isoformat()})


@require_POST
def import_omron_csv(request: HttpRequest) -> HttpResponse:
    uploaded_file = request.FILES.get("csv_file")
    if uploaded_file is None:
        messages.error(request, "CSV ファイルを選択してください。")
        return redirect("bodylog:dashboard")

    try:
        imported_count = import_uploaded_csv(uploaded_file)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("bodylog:dashboard")

    messages.success(request, f"{imported_count} 件の体重データを取り込みました。")
    return redirect("bodylog:dashboard")
