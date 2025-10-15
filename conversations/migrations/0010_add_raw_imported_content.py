# Generated manually on 2025-10-15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0009_add_continuation_message_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='raw_imported_content',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
