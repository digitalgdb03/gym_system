from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "requires_trainer", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("name",)
