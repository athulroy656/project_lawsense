# Generated manually for report caching fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0006_document_user'),  # Depends on the latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='report_cache',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='report_cached_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='report_cache_key',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
