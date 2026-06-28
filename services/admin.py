from django.contrib import admin
from .models import Servicio

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "color", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("nombre",)