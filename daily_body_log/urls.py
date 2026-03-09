"""管理画面と bodylog アプリへ URL を振り分ける親ルーター。"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("bodylog.urls")),
]
