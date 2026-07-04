from django.urls import path
from . import views

app_name = "report"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("reportes/", views.reports, name="reports"),
    path("reportes/pdf/", views.reports_pdf, name="reports_pdf"),
]
