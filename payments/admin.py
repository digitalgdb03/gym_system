from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("client", "plan", "amount_usd", "currency", "method", "created_at")
    list_filter = ("method", "currency", "created_at")
    search_fields = ("client__full_name",)
