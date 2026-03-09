from pathlib import Path

from django.core.management.base import BaseCommand

from bodylog.importers import import_csv_records


class Command(BaseCommand):
    help = "CSV の既存記録を Django の SQLite DB に取り込みます"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--path",
            default="data/records.csv",
            help="取り込む CSV ファイルのパス",
        )

    def handle(self, *args, **options) -> None:
        csv_path = Path(options["path"])
        count = import_csv_records(csv_path)
        self.stdout.write(self.style.SUCCESS(f"{count} 件を取り込みました: {csv_path}"))
