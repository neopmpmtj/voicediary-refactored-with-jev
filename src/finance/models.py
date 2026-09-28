import uuid

from django.conf import settings
from django.db import models

from src.diary.models import Entry


class RecordStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class ItemType(models.TextChoices):
    EXPENSE = "expense", "Expense"
    INCOME = "income", "Income"


class FinancialRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="finance_records",
    )
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="finance_records",
        null=True,
        blank=True,
    )
    record_name = models.CharField(max_length=255, blank=True, default="")
    record_context = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=RecordStatus.choices)
    error_message = models.TextField(blank=True, default="")
    llm_response = models.JSONField(default=dict, blank=True)
    external_id = models.CharField(max_length=255, blank=True, default="")
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "external_id"],
                condition=~models.Q(external_id=""),
                name="uniq_user_finance_external_id",
            ),
        ]

    def __str__(self):
        return f"{self.record_name or 'finance'} {self.status}"


class FinancialItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    financial_record = models.ForeignKey(
        FinancialRecord,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_index = models.PositiveIntegerField()
    type = models.CharField(
        max_length=16,
        choices=ItemType.choices,
        default=ItemType.EXPENSE,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="EUR")
    category = models.CharField(max_length=100, blank=True, default="")
    merchant = models.CharField(max_length=255, blank=True, default="")
    transaction_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    payment_method = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["item_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["financial_record", "item_index"],
                name="uniq_finance_record_item_index",
            ),
        ]

    def __str__(self):
        return f"#{self.item_index}: {self.type} {self.amount} {self.currency}"
