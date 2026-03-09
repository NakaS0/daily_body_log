"""日別の記録データをデータベースに保存するモデル定義。"""

from django.db import models


class DailyRecord(models.Model):
    """朝昼夕の食事、体重、内臓脂肪、運動、備考を 1 日単位で保持する。"""

    log_date = models.DateField(unique=True)
    breakfast = models.CharField(max_length=255, blank=True)
    lunch = models.CharField(max_length=255, blank=True)
    dinner = models.CharField(max_length=255, blank=True)
    weight_kg = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    visceral_fat_level = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    exercise = models.CharField(max_length=255, blank=True)
    execution = models.CharField(max_length=255, blank=True)
    replacement_achieved = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["log_date"]

    def __str__(self) -> str:
        """管理画面やデバッグ表示で見やすいように日付文字列を返す。"""
        return self.log_date.isoformat()
