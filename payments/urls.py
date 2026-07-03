from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("", views.PaymentList.as_view(), name="list"),
    path("nuevo/", views.PaymentCreate.as_view(), name="create"),
    path("<int:pk>/editar/", views.PaymentUpdate.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.PaymentDelete.as_view(), name="delete"),
]
