from django.urls import path
from . import views

app_name = "client"

urlpatterns = [
    path("", views.ClientList.as_view(), name="list"),
    path("nuevo/", views.ClientCreate.as_view(), name="create"),
    path("<int:pk>/editar/", views.ClientUpdate.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.ClientDelete.as_view(), name="delete"),
    path("<int:pk>/", views.client_detail, name="detail"),
    path("<int:pk>/membresia/", views.membership_add, name="membership_add"),
    path("membresia/<int:pk>/eliminar/", views.membership_remove, name="membership_remove"),
    path("<int:pk>/congelar/", views.client_freeze, name="freeze"),
    path("<int:pk>/descongelar/", views.client_unfreeze, name="unfreeze"),
]
