from django.contrib import admin

from src.diary.models import Attachment, Entry, UsageLog


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "item_type", "route", "intent", "subject", "reference")
    list_filter = ("item_type", "route")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("uploaded_at", "user", "original_filename", "entry")
    list_filter = ("uploaded_at",)


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "service", "usage_type", "amount")
