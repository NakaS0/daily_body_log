from django.db import models


class DailyRecord(models.Model):
    log_date = models.DateField(unique=True)
    breakfast = models.CharField(max_length=255, blank=True)
    lunch = models.CharField(max_length=255, blank=True)
    dinner = models.CharField(max_length=255, blank=True)
    weight_kg = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    visceral_fat_level = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    exercise = models.CharField(max_length=255, blank=True)
    execution = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["log_date"]

    def __str__(self) -> str:
        return self.log_date.isoformat()
