from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    """Add index to expires_at for efficient expired token cleanup queries."""

    dependencies: ClassVar = [
        ('blocklist', '0002_alter_blocklistedjwtoken_options'),
    ]

    operations: ClassVar = [
        migrations.AlterField(
            model_name='blocklistedjwtoken',
            name='expires_at',
            field=models.DateTimeField(db_index=True),
        ),
    ]
