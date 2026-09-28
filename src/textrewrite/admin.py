from django.contrib import admin

from src.textrewrite.models import RewriteUsage


@admin.register(RewriteUsage)
class RewriteUsageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "model_id", "style", "input_tokens", "output_tokens")
