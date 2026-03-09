"""DailyRecord モデルを新規作成する初回 migration。"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """テーブル作成に必要な操作を定義する。"""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DailyRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("log_date", models.DateField(unique=True)),
                ("breakfast", models.CharField(blank=True, max_length=255)),
                ("lunch", models.CharField(blank=True, max_length=255)),
                ("dinner", models.CharField(blank=True, max_length=255)),
                ("weight_kg", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                (
                    "visceral_fat_level",
                    models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
                ),
                ("exercise", models.CharField(blank=True, max_length=255)),
                ("execution", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["log_date"]},
        ),
    ]
