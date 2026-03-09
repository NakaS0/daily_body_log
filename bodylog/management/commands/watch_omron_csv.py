"""監視フォルダに置かれた OMRON CSV を自動で取り込む管理コマンド。"""

import time
from pathlib import Path

from django.core.management.base import BaseCommand

from bodylog.importers import import_csv_records, move_processed_file


class Command(BaseCommand):
    """監視ループを回しながら CSV を順次取り込む。"""

    help = "監視フォルダに置かれた OMRON CSV を自動取り込みします"

    def add_arguments(self, parser) -> None:
        """監視対象フォルダや待機秒数などの実行オプションを定義する。"""
        parser.add_argument(
            "--watch-dir",
            default="data/omron_inbox",
            help="監視する CSV フォルダ",
        )
        parser.add_argument(
            "--processed-dir",
            default="data/omron_processed",
            help="取り込み成功後の退避先",
        )
        parser.add_argument(
            "--failed-dir",
            default="data/omron_failed",
            help="取り込み失敗時の退避先",
        )
        parser.add_argument(
            "--poll-seconds",
            type=int,
            default=5,
            help="監視間隔（秒）",
        )
        parser.add_argument(
            "--stable-seconds",
            type=int,
            default=3,
            help="更新直後ファイルを待つ秒数",
        )

    def handle(self, *args, **options) -> None:
        """監視先の準備を行い、停止されるまで取り込みループを回す。"""
        watch_dir = Path(options["watch_dir"])
        processed_dir = Path(options["processed_dir"])
        failed_dir = Path(options["failed_dir"])
        poll_seconds = max(1, options["poll_seconds"])
        stable_seconds = max(1, options["stable_seconds"])

        watch_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        failed_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.SUCCESS(f"監視開始: {watch_dir.resolve()}"))
        self.stdout.write(f"成功時: {processed_dir.resolve()}")
        self.stdout.write(f"失敗時: {failed_dir.resolve()}")
        self.stdout.write("停止するには Ctrl+C を押してください。")

        # 定期的に監視フォルダを確認し、新しい CSV があれば処理する。
        try:
            while True:
                self._process_pending_files(
                    watch_dir=watch_dir,
                    processed_dir=processed_dir,
                    failed_dir=failed_dir,
                    stable_seconds=stable_seconds,
                )
                time.sleep(poll_seconds)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("監視を停止しました。"))

    def _process_pending_files(
        self,
        watch_dir: Path,
        processed_dir: Path,
        failed_dir: Path,
        stable_seconds: int,
    ) -> None:
        """書き込み完了済みの CSV だけを判定して取り込み・退避する。"""
        now = time.time()
        csv_files = sorted(path for path in watch_dir.glob("*.csv") if path.is_file())

        for csv_path in csv_files:
            if now - csv_path.stat().st_mtime < stable_seconds:
                continue

            try:
                imported_count = import_csv_records(csv_path)
                archived_path = move_processed_file(csv_path, processed_dir)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"取込成功: {archived_path.name} ({imported_count} 件)"
                    )
                )
            except Exception as exc:
                failed_path = move_processed_file(csv_path, failed_dir)
                self.stderr.write(
                    self.style.ERROR(f"取込失敗: {failed_path.name} ({exc})")
                )
