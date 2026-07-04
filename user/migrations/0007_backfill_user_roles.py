# Generated manually (part 2/3 of role -> roles migration): backfill roles from the old role field.

from django.db import migrations


def backfill_roles(apps, schema_editor):
    User = apps.get_model('user', 'User')
    for user in User.objects.all():
        if user.role:
            user.roles = [user.role]
            user.save(update_fields=['roles'])


def reverse_backfill(apps, schema_editor):
    User = apps.get_model('user', 'User')
    for user in User.objects.all():
        user.roles = []
        user.save(update_fields=['roles'])


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_user_roles'),
    ]

    operations = [
        migrations.RunPython(backfill_roles, reverse_backfill),
    ]
