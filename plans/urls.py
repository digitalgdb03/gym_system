from django.urls import path
from . import views

app_name = "plans"

urlpatterns = [
    path("", views.plan_list, name="list"),
    path("nuevo/", views.PlanCreateView.as_view(), name="create"),
    path("<int:pk>/editar/", views.PlanUpdateView.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.PlanDeleteView.as_view(), name="delete"),
]