from django.contrib import admin

from .models import DailyRecord


@admin.register(DailyRecord)
class DailyRecordAdmin(admin.ModelAdmin):
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
