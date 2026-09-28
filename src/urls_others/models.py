import uuid

from django.conf import settings
from django.db import models

from src.diary.models import Entry


class ReferenceKind(models.TextChoices):
    URL = "url", "URL"
    ENDPOINT = "endpoint", "Endpoint"


class ReferenceStatus(models.TextChoices):
    PENDING = "pending", "Pending"


class Reference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="url_references",
    )
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="references")
    kind = models.CharField(max_length=16, choices=ReferenceKind.choices)
    value = models.TextField()
    note = models.TextField(blank=True, default="")
    title = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    transcript = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=ReferenceStatus.choices,
        default=ReferenceStatus.PENDING,
    )
    error = models.TextField(blank=True, default="")
    fetched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.value}"
