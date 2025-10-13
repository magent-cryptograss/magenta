# Generated manually

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0005_message_is_retry_message_is_synthetic_error'),
    ]

    operations = [
        # Step 1: Drop the old primary key constraint
        migrations.RunSQL(
            "ALTER TABLE conversations_compactingaction DROP CONSTRAINT conversations_compactingaction_pkey;",
            reverse_sql="ALTER TABLE conversations_compactingaction ADD PRIMARY KEY (context_window_id);"
        ),

        # Step 2: Add new UUID primary key field
        migrations.AddField(
            model_name='compactingaction',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=False),
        ),

        # Step 3: Set the id field as primary key
        migrations.RunSQL(
            "ALTER TABLE conversations_compactingaction ADD PRIMARY KEY (id);",
            reverse_sql="ALTER TABLE conversations_compactingaction DROP CONSTRAINT conversations_compactingaction_pkey;"
        ),

        # Step 4: Make context_window nullable and not primary key
        migrations.AlterField(
            model_name='compactingaction',
            name='context_window',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='compacting_action',
                to='conversations.contextwindow'
            ),
        ),

        # Step 5: Make ending_message_id nullable
        migrations.AlterField(
            model_name='compactingaction',
            name='ending_message_id',
            field=models.UUIDField(blank=True, null=True),
        ),

        # Step 6: Rename table
        migrations.AlterModelTable(
            name='compactingaction',
            table='compacting_actions',
        ),
    ]
