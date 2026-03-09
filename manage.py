#!/usr/bin/env python
"""このプロジェクトで Django の管理コマンドを起動する入口ファイル。"""

import os
import sys


def main() -> None:
    """設定モジュールを用意して、指定された Django コマンドを実行する。"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daily_body_log.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
