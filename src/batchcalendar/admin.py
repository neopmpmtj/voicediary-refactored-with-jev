from django.contrib import admin

from src.batchcalendar.models import CalendarBooking


@admin.register(CalendarBooking)
class CalendarBookingAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "summary", "status", "start_datetime")
    list_filter = ("status",)
