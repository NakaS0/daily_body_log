"""現在の DailyRecord を JSON fixture として書き出す管理コマンド。"""

from pathlib import Path

from django.core.management.base import BaseCommand

from bodylog.importers import export_json_fixture


class Command(BaseCommand):
    """CLI から DailyRecord を JSON fixture に書き出す。"""

    help = "現在の DailyRecord を JSON fixture に書き出します"

    def add_arguments(self, parser) -> None:
        """書き出し先 JSON ファイルのパスを受け取る。"""
        parser.add_argument(
            "--path",
            required=True,
            help="書き出し先 JSON ファイルのパス",
        )

    def handle(self, *args, **options) -> None:
        """現在の DB を指定ファイルへ書き出し、件数を表示する。"""
        json_path = Path(options["path"])
        count = export_json_fixture(json_path)
        self.stdout.write(self.style.SUCCESS(f"{count} 件を書き出しました: {json_path}"))
