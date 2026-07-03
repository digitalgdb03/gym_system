from django.contrib import admin
from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("label", "service", "duration", "price_bcv", "price_cash", "is_active")
    list_filter = ("service", "duration", "is_active")
    filter_horizontal = ("included_services",)
