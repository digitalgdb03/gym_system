from django.urls import path
from . import views

app_name = "configuration"

urlpatterns = [
    path("", views.edit, name="edit"),
    path("tasa/guardar/", views.save_rate, name="save_rate"),
    path("tasa/actualizar/", views.refresh_bcv, name="refresh_bcv"),
]