"""指定した CSV ファイルを手動で取り込む Django 管理コマンド。"""

from pathlib import Path

from django.core.management.base import BaseCommand

from bodylog.importers import import_csv_records


class Command(BaseCommand):
    """CLI から CSV 取り込みを実行する。"""

    help = "指定した CSV を Django の SQLite DB に取り込みます"

    def add_arguments(self, parser) -> None:
        """コマンド実行時に受け取る引数を定義する。"""
        parser.add_argument(
            "--path",
            required=True,
            help="取り込む CSV ファイルのパス",
        )

    def handle(self, *args, **options) -> None:
        """指定パスの CSV を読み込み、取り込み件数を表示する。"""
        csv_path = Path(options["path"])
        count = import_csv_records(csv_path)
        self.stdout.write(self.style.SUCCESS(f"{count} 件を取り込みました: {csv_path}"))
