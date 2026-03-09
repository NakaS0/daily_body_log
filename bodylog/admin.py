"""Django 管理画面で DailyRecord を見やすく表示するための設定。"""

from django.contrib import admin

from .models import DailyRecord


@admin.register(DailyRecord)
class DailyRecordAdmin(admin.ModelAdmin):
    """一覧表示項目や検索対象を指定して、管理画面の使い勝手を整える。"""

    list_display = (
        "log_date",
        "breakfast",
        "lunch",
        "dinner",
        "weight_kg",
        "visceral_fat_level",
    )
    ordering = ("-log_date",)
    search_fields = ("log_date", "breakfast", "lunch", "dinner", "exercise", "execution")
