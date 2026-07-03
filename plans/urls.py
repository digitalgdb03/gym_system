from django.urls import path
from . import views

app_name = "plans"

urlpatterns = [
    path("", views.PlanList.as_view(), name="list"),
    path("nuevo/", views.PlanCreate.as_view(), name="create"),
    path("<int:pk>/editar/", views.PlanUpdate.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.PlanDelete.as_view(), name="delete"),
]
