"""ダッシュボード画面、分析画面、保存 API をまとめたビュー定義。"""

import calendar
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .importers import import_uploaded_csv
from .models import DailyRecord

BREAKFAST_OPTIONS = [
    "活力＋VM1122",
    "推奨食事",
    "サボリ",
    "なし",
]

LUNCH_OPTIONS = [
    "D24＋推奨食事",
    "D24＋ジュニアバランス",
    "外食",
    "サボリ",
    "なし",
]

DINNER_OPTIONS = [
    "NB",
    "活力＋VM1122",
    "外食",
    "サボリ",
    "なし",
]

MEAL_SEPARATOR = " / "
WEEKDAY_LABELS = ["月", "火", "水", "木", "金", "土", "日"]


def _build_exercise_options() -> list[str]:
    """運動時間プルダウン用に 30 分刻みの候補文字列を作る。"""
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


def _normalize_meal_value(value: str) -> str:
    """旧値「不明」を新値「なし」へ読み替える。"""
    return "なし" if value == "不明" else value


def _parse_optional_decimal(raw_value: str, field_label: str) -> Decimal | None:
    """空欄を許容しつつ、数値入力を Decimal に正規化する。"""
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
    """保存済み文字列を画面側で扱いやすい単一選択リストに変換する。"""
    if not raw_value.strip():
        return []
    return [raw_value.split(MEAL_SEPARATOR)[0].strip()]


def _join_multi_value(values: list[str]) -> str:
    """画面から受け取った候補値のうち、有効な 1 件だけを保存形式へ戻す。"""
    for value in values:
        stripped = value.strip()
        if stripped:
            return stripped
    return ""


def _replacement_count(breakfast: str, lunch: str, dinner: str) -> str:
    """朝昼夕の組み合わせから 2 食置き換えか 3 食置き換えかを判定する。"""
    if breakfast == "活力＋VM1122" and lunch == "D24＋ジュニアバランス" and dinner == "NB":
        return "3食"
    if breakfast == "活力＋VM1122" and lunch == "D24＋推奨食事" and dinner == "NB":
        return "2食"
    return ""


def _is_replacement_complete(breakfast: str, lunch: str, dinner: str) -> bool:
    """達成条件を満たす 2 食または 3 食置き換えかどうかを返す。"""
    return _replacement_count(breakfast, lunch, dinner) in {"2食", "3食"}


def _replacement_meal_count(breakfast: str, lunch: str, dinner: str) -> int:
    """置き換え対象の食事が何食入力されているかを数える。"""
    count = 0
    if breakfast == "活力＋VM1122":
        count += 1
    if lunch in {"D24＋推奨食事", "D24＋ジュニアバランス"}:
        count += 1
    if dinner == "NB":
        count += 1
    return count


def _lifestyle_tone(breakfast: str, lunch: str, dinner: str) -> str:
    """食生活表示やカレンダー表示に使う状態名を返す。"""
    if not breakfast and not lunch and not dinner:
        return "empty"
    replacement_meal_count = _replacement_meal_count(breakfast, lunch, dinner)
    if replacement_meal_count >= 2:
        return "good"
    if replacement_meal_count >= 1:
        return "middle"
    return "bad"


def _calendar_symbol(breakfast: str, lunch: str, dinner: str) -> str:
    """分析ページのカレンダー内に出す記号を決める。"""
    tone = _lifestyle_tone(breakfast, lunch, dinner)
    if tone == "good":
        return "◎"
    if tone == "middle":
        return "○"
    if tone == "bad":
        return "△"
    return "-"


def _parse_exercise_minutes(exercise: str) -> int:
    """運動時間の表示文字列を合計分へ変換して集計しやすくする。"""
    value = exercise.strip()
    if not value:
        return 0

    hours = 0
    minutes = 0
    if "時間" in value:
        hour_part, _, rest = value.partition("時間")
        if hour_part.isdigit():
            hours = int(hour_part)
        value = rest
    if "分" in value:
        minute_part = value.replace("分", "").strip()
        if minute_part.isdigit():
            minutes = int(minute_part)
    return hours * 60 + minutes


def _format_minutes_label(total_minutes: int) -> str:
    """分単位の合計値を『1時間30分』のような表示文字列へ戻す。"""
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}時間{minutes}分"
    if hours:
        return f"{hours}時間"
    return f"{minutes}分"


def _resolve_month(year: int | None, month: int | None) -> tuple[int, int] | None:
    """URL パラメータが省略された場合も含めて、表示対象の年月を確定する。"""
    today = date.today()
    display_year = year or today.year
    display_month = month or today.month
    if not 1 <= display_month <= 12:
        return None
    return display_year, display_month


def _build_month_context(display_year: int, display_month: int) -> dict[str, object]:
    """月次画面の描画に必要な一覧データと集計値をまとめて作る。"""
    today = date.today()
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
    calendar_days = []
    previous_weight = ""
    previous_visceral = ""
    monthly_total_exercise_minutes = 0
    chart_points: list[dict[str, object]] = []

    # 各日付について、表表示・カレンダー表示・グラフ表示で共通利用する
    # 中間データを 1 回のループでまとめて作成する。
    for day_number in range(1, days_in_month + 1):
        current_day = date(display_year, display_month, day_number)
        record = month_records.get(current_day)
        breakfast_value = _normalize_meal_value(record.breakfast) if record else ""
        lunch_value = _normalize_meal_value(record.lunch) if record else ""
        dinner_value = _normalize_meal_value(record.dinner) if record else ""
        weight_value = f"{record.weight_kg:.1f}" if record and record.weight_kg is not None else ""
        visceral_value = (
            f"{record.visceral_fat_level:.1f}"
            if record and record.visceral_fat_level is not None
            else ""
        )
        replacement_count = _replacement_count(breakfast_value, lunch_value, dinner_value)
        replacement_complete = _is_replacement_complete(breakfast_value, lunch_value, dinner_value)

        if record:
            monthly_total_exercise_minutes += _parse_exercise_minutes(record.exercise)

        chart_points.append(
            {
                "day": day_number,
                "label": f"{current_day.month}/{current_day.day}",
                "weight": float(weight_value) if weight_value else None,
                "visceral": float(visceral_value) if visceral_value else None,
            }
        )

        day_payload = {
            "date": current_day,
            "date_label": f"{current_day.month}/{current_day.day}（{WEEKDAY_LABELS[current_day.weekday()]}）",
            "record": record,
            "breakfast_value": breakfast_value,
            "lunch_value": lunch_value,
            "dinner_value": dinner_value,
            "breakfast_selected": _split_multi_value(breakfast_value),
            "lunch_selected": _split_multi_value(lunch_value),
            "dinner_selected": _split_multi_value(dinner_value),
            "weight_value": weight_value,
            "visceral_value": visceral_value,
            "replacement_count": replacement_count,
            "replacement_complete": replacement_complete,
            "lifestyle_tone": _lifestyle_tone(breakfast_value, lunch_value, dinner_value),
        }
        month_days.append(day_payload)
        calendar_days.append(
            {
                "date": current_day,
                "day": day_number,
                "weight_value": weight_value,
                "execution": record.execution if record else "",
                "replacement_complete": replacement_complete,
                "lifestyle_tone": _lifestyle_tone(breakfast_value, lunch_value, dinner_value),
                "calendar_symbol": _calendar_symbol(breakfast_value, lunch_value, dinner_value),
                "is_today": current_day == today,
            }
        )

        if weight_value:
            previous_weight = weight_value
        if visceral_value:
            previous_visceral = visceral_value

    today_record = month_records.get(today) or DailyRecord.objects.filter(log_date=today).first()
    prev_year, prev_month = (display_year - 1, 12) if display_month == 1 else (display_year, display_month - 1)
    next_year, next_month = (display_year + 1, 1) if display_month == 12 else (display_year, display_month + 1)

    # カレンダー表示用に、前月末・翌月初を含む週単位の配列を組み立てる。
    month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(display_year, display_month)
    calendar_weeks = []
    for week in month_calendar:
        week_cells = []
        for week_day in week:
            if week_day.month == display_month:
                match = next(day for day in calendar_days if day["date"] == week_day)
                week_cells.append(match)
            else:
                week_cells.append(
                    {
                        "date": week_day,
                        "day": week_day.day,
                        "weight_value": "",
                        "execution": "",
                        "replacement_complete": False,
                        "lifestyle_tone": "empty",
                        "calendar_symbol": "-",
                        "is_today": False,
                        "is_outside_month": True,
                    }
                )
        calendar_weeks.append(week_cells)

    return {
        "today": today,
        "today_label": f"{today.month}/{today.day}（{WEEKDAY_LABELS[today.weekday()]}）",
        "today_record": today_record,
        "today_breakfast_value": _normalize_meal_value(today_record.breakfast) if today_record else "",
        "today_lunch_value": _normalize_meal_value(today_record.lunch) if today_record else "",
        "today_dinner_value": _normalize_meal_value(today_record.dinner) if today_record else "",
        "today_breakfast_selected": _split_multi_value(_normalize_meal_value(today_record.breakfast) if today_record else ""),
        "today_lunch_selected": _split_multi_value(_normalize_meal_value(today_record.lunch) if today_record else ""),
        "today_dinner_selected": _split_multi_value(_normalize_meal_value(today_record.dinner) if today_record else ""),
        "today_weight_value": (
            f"{today_record.weight_kg:.1f}"
            if today_record and today_record.weight_kg is not None
            else ""
        ),
        "today_visceral_value": (
            f"{today_record.visceral_fat_level:.1f}"
            if today_record and today_record.visceral_fat_level is not None
            else ""
        ),
        "display_year": display_year,
        "display_month": display_month,
        "month_label": first_day.strftime("%Y年 %m月"),
        "month_days": month_days,
        "calendar_weeks": calendar_weeks,
        "calendar_weekday_labels": WEEKDAY_LABELS,
        "monthly_total_exercise_label": _format_minutes_label(monthly_total_exercise_minutes),
        "chart_points": chart_points,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "breakfast_options": BREAKFAST_OPTIONS,
        "lunch_options": LUNCH_OPTIONS,
        "dinner_options": DINNER_OPTIONS,
        "exercise_options": EXERCISE_OPTIONS,
    }


def dashboard(request: HttpRequest, year: int | None = None, month: int | None = None) -> HttpResponse:
    """記録ページを表示する。"""
    resolved = _resolve_month(year, month)
    if resolved is None:
        return redirect("bodylog:dashboard")
    display_year, display_month = resolved
    context = _build_month_context(display_year, display_month)
    return render(request, "bodylog/dashboard.html", context)


def analysis(request: HttpRequest, year: int | None = None, month: int | None = None) -> HttpResponse:
    """分析ページを表示する。"""
    resolved = _resolve_month(year, month)
    if resolved is None:
        return redirect("bodylog:analysis")
    display_year, display_month = resolved
    context = _build_month_context(display_year, display_month)
    return render(request, "bodylog/analysis.html", context)


@require_POST
def save_record(request: HttpRequest, date_value: str) -> JsonResponse:
    """1 日分の入力値を保存し、保存結果を JSON で返す。"""
    try:
        log_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        breakfast = _normalize_meal_value(_join_multi_value(_split_multi_value(request.POST.get("breakfast", ""))))
        lunch = _normalize_meal_value(_join_multi_value(_split_multi_value(request.POST.get("lunch", ""))))
        dinner = _normalize_meal_value(_join_multi_value(_split_multi_value(request.POST.get("dinner", ""))))
        weight_kg = _parse_optional_decimal(request.POST.get("weight_kg", ""), "体重")
        visceral_fat_level = _parse_optional_decimal(
            request.POST.get("visceral_fat_level", ""),
            "内臓脂肪",
        )
        exercise = request.POST.get("exercise", "").strip()
        execution = request.POST.get("execution", "").strip()
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    # 何も入力されていない日付はレコードを削除し、
    # 何か入っている場合だけ保存対象として扱う。
    replacement_achieved = _is_replacement_complete(breakfast, lunch, dinner)
    has_any = any(
        [
            breakfast,
            lunch,
            dinner,
            weight_kg is not None,
            visceral_fat_level is not None,
            exercise,
            execution,
            replacement_achieved,
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
    record.replacement_achieved = replacement_achieved
    record.save()
    return JsonResponse(
        {
            "ok": True,
            "status": "saved",
            "date": log_date.isoformat(),
            "replacement_achieved": replacement_achieved,
        }
    )


@require_POST
def import_omron_csv(request: HttpRequest) -> HttpResponse:
    """画面からアップロードされた OMRON CSV を取り込む。"""
    uploaded_file = request.FILES.get("csv_file")
    if uploaded_file is None:
        messages.error(request, "CSVファイルを選択してください。")
        return redirect("bodylog:dashboard")

    try:
        imported_count = import_uploaded_csv(uploaded_file)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("bodylog:dashboard")

    messages.success(request, f"{imported_count}件の体重データを取り込みました。")
    return redirect("bodylog:dashboard")
