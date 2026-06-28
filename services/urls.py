from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("", views.ServicioListView.as_view(), name="list"),
    path("nuevo/", views.ServicioCreateView.as_view(), name="create"),
    path("<int:pk>/editar/", views.ServicioUpdateView.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.ServicioDeleteView.as_view(), name="delete"),
]
