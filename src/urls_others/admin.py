from django.contrib import admin

from src.urls_others.models import Reference


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "kind", "status", "value")
    list_filter = ("kind", "status")
