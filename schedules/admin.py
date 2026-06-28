from django.contrib import admin
from .models import GymClass


@admin.register(GymClass)
class GymClassAdmin(admin.ModelAdmin):
    list_display = ("service", "get_day_display", "block", "kind", "instructor", "second_instructor")
    list_filter = ("day", "kind", "service")
