import uuid

from django.conf import settings
from django.db import models

from src.diary.models import Entry


class BookingStatus(models.TextChoices):
    INSERTED = "inserted", "Inserted"
    TAKEN = "taken", "Taken"
    FAILED = "failed", "Failed"


class CalendarBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_bookings",
    )
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="calendar_bookings",
    )
    event_index = models.PositiveIntegerField()
    summary = models.CharField(max_length=255, blank=True, default="")
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, blank=True, default="Europe/Lisbon")
    status = models.CharField(max_length=16, choices=BookingStatus.choices)
    problem = models.TextField(blank=True, default="")
    google_event_id = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["event_index", "created_at"]

    def __str__(self):
        return f"{self.summary or 'calendar'} {self.status}"
