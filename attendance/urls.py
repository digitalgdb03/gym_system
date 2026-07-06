from django.urls import path
from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.attendance_list, name="list"),
    path("marcar/", views.mark_entry, name="mark"),
    path("registrar/", views.register_client, name="register"),
    path("<int:pk>/salida/", views.check_out, name="checkout"),
]
