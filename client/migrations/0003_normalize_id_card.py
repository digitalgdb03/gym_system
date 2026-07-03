from django.db import migrations, transaction


def strip_id_card(apps, schema_editor):
    Client = apps.get_model("client", "Client")
    for client in Client.objects.all():
        cleaned = (client.id_card or "").replace(".", "").replace("-", "").strip()
        if cleaned != client.id_card:
            try:
                with transaction.atomic():
                    client.id_card = cleaned
                    client.save(update_fields=["id_card"])
            except Exception:
                # Ya existe otro cliente cuya cédula normalizada coincide; requiere revisión manual.
                pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("client", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(strip_id_card, noop),
    ]
