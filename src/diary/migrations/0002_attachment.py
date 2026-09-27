import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("diary", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Attachment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("original_filename", models.CharField(max_length=255)),
                ("stored_name", models.CharField(max_length=255)),
                ("mime_type", models.CharField(blank=True, default="", max_length=120)),
                ("relative_path", models.CharField(max_length=500)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="diary.entry",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["uploaded_at"],
            },
        ),
    ]
