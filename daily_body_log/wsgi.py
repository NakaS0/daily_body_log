"""一般的な WSGI サーバーから利用される Django アプリの起点。"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daily_body_log.settings")

application = get_wsgi_application()
