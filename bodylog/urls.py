from django.urls import path

from . import views

app_name = "bodylog"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("<int:year>/<int:month>/", views.dashboard, name="dashboard_month"),
    path("analysis/", views.analysis, name="analysis"),
    path("analysis/<int:year>/<int:month>/", views.analysis, name="analysis_month"),
    path("import/omron-csv/", views.import_omron_csv, name="import_omron_csv"),
    path("api/records/<str:date_value>/", views.save_record, name="save_record"),
]
