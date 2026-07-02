from django.urls import path
from . import views

app_name = "configuration"

urlpatterns = [
    path("", views.ConfigUpdateView.as_view(), name="edit"),
    path("tasa/actualizar/", views.refresh_bcv, name="refresh_bcv"),
]
