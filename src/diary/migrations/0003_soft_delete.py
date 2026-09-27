from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("diary", "0002_attachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="attachment",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attachment",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="entry",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="entry",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
    ]
