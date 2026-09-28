from django.contrib import admin

from src.conferencerewrite.models import RewriteUsage


@admin.register(RewriteUsage)
class RewriteUsageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "model_id", "input_tokens", "output_tokens")
