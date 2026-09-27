from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conference", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="segment",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="segment",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
    ]
