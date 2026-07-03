from django.urls import path
from . import views

app_name = "schedules"

urlpatterns = [
    path("", views.ScheduleList.as_view(), name="calendar"),
    path("nueva/", views.ClassCreate.as_view(), name="create"),
    path("<int:pk>/editar/", views.ClassUpdate.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.ClassDelete.as_view(), name="delete"),
]
