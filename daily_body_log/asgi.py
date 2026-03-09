"""ASGI 対応サーバーから利用される Django アプリの起点。"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daily_body_log.settings")

application = get_asgi_application()
