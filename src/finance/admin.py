from django.contrib import admin

from src.finance.models import FinancialItem, FinancialRecord


class FinancialItemInline(admin.TabularInline):
    model = FinancialItem
    extra = 0


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "record_name", "status")
    list_filter = ("status",)
    inlines = [FinancialItemInline]
