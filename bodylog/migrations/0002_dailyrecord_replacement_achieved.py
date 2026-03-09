"""DailyRecord に置き換え達成フラグを追加する migration。"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """既存テーブルへ replacement_achieved 列を追加する。"""

    dependencies = [
        ("bodylog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyrecord",
            name="replacement_achieved",
            field=models.BooleanField(default=False),
        ),
    ]
