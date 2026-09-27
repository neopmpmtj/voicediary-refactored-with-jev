import uuid

from django.conf import settings
from django.db import models


class ConferenceStatus(models.TextChoices):
    OPEN = "open", "Open"
    COMPLETE = "complete", "Complete"


class Conference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conferences")
    status = models.CharField(max_length=16, choices=ConferenceStatus.choices, default=ConferenceStatus.OPEN)
    content_text = models.TextField(blank=True, default="")
    total_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user_id} conference {self.id}"


class Segment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name="segments")
    sequence = models.PositiveIntegerField()
    content_text = models.TextField(blank=True, default="")
    transcription_error = models.TextField(blank=True, default="")
    recording_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    processed_duration_seconds = models.FloatField(null=True, blank=True)
    relative_path = models.CharField(max_length=500)
    processed_relative_path = models.CharField(max_length=500, blank=True, default="")
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(fields=["conference", "sequence"], name="uniq_conference_segment_sequence"),
        ]

    def __str__(self):
        return f"{self.conference_id} #{self.sequence}"
