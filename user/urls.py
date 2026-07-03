from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "user"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(
        template_name="user/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("", views.StaffList.as_view(), name="list"),
    path("nuevo/", views.StaffCreate.as_view(), name="create"),
    path("<int:pk>/editar/", views.StaffUpdate.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.StaffDelete.as_view(), name="delete"),
    path("mi-perfil/", views.profile_edit, name="profile"),
]
