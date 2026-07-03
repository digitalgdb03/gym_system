from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "full_name", "role", "id_card", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Datos del gimnasio", {"fields": ("full_name", "role", "id_card", "phone", "detail", "disciplines")}),
    )
