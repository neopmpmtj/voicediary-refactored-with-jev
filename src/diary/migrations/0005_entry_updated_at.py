from django.db import migrations, models
from django.db.models import F
from django.utils import timezone


def backfill_updated_at(apps, schema_editor):
    Entry = apps.get_model("diary", "Entry")
    Entry.objects.update(updated_at=F("created_at"))


class Migration(migrations.Migration):

    dependencies = [
        ("diary", "0004_entry_reference_entry_reference_confidence_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="entry",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_updated_at, migrations.RunPython.noop),
    ]
