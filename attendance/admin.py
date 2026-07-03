from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("client", "check_in", "check_out", "is_inside")
    list_filter = ("check_in",)
    search_fields = ("client__full_name", "client__id_card")
