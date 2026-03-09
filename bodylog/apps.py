"""bodylog アプリの基本設定を登録するファイル。"""

from django.apps import AppConfig


class BodylogConfig(AppConfig):
    """アプリ名や自動採番の既定値など、アプリ単位の設定を定義する。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "bodylog"
