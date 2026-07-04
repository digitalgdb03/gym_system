# Generated manually (part 3/3 of role -> roles migration)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_backfill_user_roles'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),
    ]
