from django.contrib import admin
from .models import GymConfig


@admin.register(GymConfig)
class GymConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "bcv_rate")
