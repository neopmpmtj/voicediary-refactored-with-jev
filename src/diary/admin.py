from django.contrib import admin

from diary.models import Entry, UsageLog


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "item_type", "route", "intent", "subject")
    list_filter = ("item_type", "route")


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "service", "usage_type", "amount")
