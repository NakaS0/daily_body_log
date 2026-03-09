from django.db import migrations, models


class Migration(migrations.Migration):
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
