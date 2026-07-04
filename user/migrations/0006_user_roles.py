# Generated manually (part 1/3 of role -> roles migration)

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_user_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='roles',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(choices=[('ADMIN', 'Administrador'), ('EMPLOYEE', 'Empleado'), ('INSTRUCTOR', 'Instructor')], max_length=12),
                blank=True, default=list, size=None, verbose_name='Roles',
            ),
        ),
    ]
