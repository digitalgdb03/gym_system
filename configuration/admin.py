from django.contrib import admin
from .models import ExchangeRate, GymConfig


@admin.register(GymConfig)
class GymConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "bcv_rate")

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("date", "rate", "source", "updated_at")
    list_filter = ("source",)
    ordering = ("-date",)