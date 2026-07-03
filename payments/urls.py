from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("", views.PaymentList.as_view(), name="list"),
    path("nuevo/", views.PaymentCreate.as_view(), name="create"),
]
