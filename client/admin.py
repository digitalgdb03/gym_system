from django.contrib import admin
from .models import Client, Membership, Freeze


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "doc_type", "id_card", "status", "phone")
    list_filter = ("status",)
    search_fields = ("full_name", "id_card")
    inlines = [MembershipInline]


admin.site.register(Freeze)
