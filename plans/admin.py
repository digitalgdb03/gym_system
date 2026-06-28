from django.contrib import admin
from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("etiqueta", "area", "duracion", "usd_bcv", "usd_divisas", "activo")
    list_filter = ("area", "duracion", "activo")
    filter_horizontal = ("incluye",)
