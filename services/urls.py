from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.ServiceList.as_view(), name="list"),
    path("nueva/", views.ServiceCreate.as_view(), name="create"),
    path("<int:pk>/editar/", views.ServiceUpdate.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.ServiceDelete.as_view(), name="delete"),
]
