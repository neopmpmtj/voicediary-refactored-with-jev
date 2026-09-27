import uuid

from django.conf import settings
from django.db import models


class ItemType(models.TextChoices):
    AUDIO = "audio", "Audio"
    TEXT = "text", "Text"


class Entry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries")
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    content_text = models.TextField(blank=True, default="")
    recording_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    processed_duration_seconds = models.FloatField(null=True, blank=True)
    recording_group_id = models.UUIDField(null=True, blank=True)
    intent = models.CharField(max_length=32, blank=True, default="")
    subject = models.CharField(max_length=32, blank=True, default="")
    intent_confidence = models.FloatField(null=True, blank=True)
    subject_confidence = models.FloatField(null=True, blank=True)
    user_asked_for_diary = models.BooleanField(default=False)
    user_asked_for_diary_probability = models.FloatField(null=True, blank=True)
    continues_prior = models.BooleanField(default=False)
    continues_prior_probability = models.FloatField(null=True, blank=True)
    route = models.CharField(max_length=32, blank=True, default="")
    classification_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} {self.item_type} {self.id}"


class UsageLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usage_logs")
    entry = models.ForeignKey(Entry, null=True, blank=True, on_delete=models.CASCADE, related_name="usage_logs")
    service = models.CharField(max_length=50)
    usage_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.service} {self.usage_type} {self.amount}"
