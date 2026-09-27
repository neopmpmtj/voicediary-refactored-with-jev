from django.contrib import admin

from src.conference.models import Conference, Segment


class SegmentInline(admin.TabularInline):
    model = Segment
    extra = 0


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ("started_at", "user", "status", "total_duration_seconds")
    list_filter = ("status",)
    inlines = [SegmentInline]


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ("created_at", "conference", "sequence", "recording_duration_seconds")
