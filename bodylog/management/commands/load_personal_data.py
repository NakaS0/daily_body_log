"""普段使い用 JSON データを Django DB に取り込む管理コマンド。"""

from pathlib import Path

from django.core.management.base import BaseCommand

from bodylog.importers import import_json_fixture


class Command(BaseCommand):
    """CLI から personal 用 JSON fixture を DailyRecord に反映する。"""

    help = "personal 用 JSON データを DailyRecord に取り込みます"

    def add_arguments(self, parser) -> None:
        """取り込む JSON ファイルのパスを受け取る。"""
        parser.add_argument(
            "--path",
            default="data/personal_daily_records.json",
            help="取り込む JSON ファイルのパス。既定値は data/personal_daily_records.json",
        )

    def handle(self, *args, **options) -> None:
        """指定された personal 用 JSON fixture を読み込み、件数を表示する。"""
        json_path = Path(options["path"])
        count = import_json_fixture(json_path)
        self.stdout.write(self.style.SUCCESS(f"{count} 件を取り込みました: {json_path}"))
