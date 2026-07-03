from django.db import migrations


def strip_id_card(apps, schema_editor):
    User = apps.get_model("user", "User")
    for user in User.objects.exclude(id_card=""):
        cleaned = (user.id_card or "").replace(".", "").replace("-", "").strip()
        if cleaned != user.id_card:
            user.id_card = cleaned
            user.save(update_fields=["id_card"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0002_remove_user_discipline_user_disciplines"),
    ]

    operations = [
        migrations.RunPython(strip_id_card, noop),
    ]
