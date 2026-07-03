import re
from datetime import time
from django.db import migrations, models

BLOCK_TIMES = {
    "8:40-10:30 am": (time(8, 40), time(10, 30)),
    "9:00-11:00 am": (time(9, 0), time(11, 0)),
    "2:40-3:50 pm":  (time(14, 40), time(15, 50)),
    "6:00-7:00 pm":  (time(18, 0), time(19, 0)),
    "7:00-8:00 pm":  (time(19, 0), time(20, 0)),
    "8:00-9:00 pm":  (time(20, 0), time(21, 0)),
    "9:00-10:00 pm": (time(21, 0), time(22, 0)),
}


def _parse_block(value):
    if value in BLOCK_TIMES:
        return BLOCK_TIMES[value]
    m = re.match(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})\s*(am|pm)", value or "", re.I)
    if not m:
        return time(8, 0), time(9, 0)
    h1, m1, h2, m2, meridiem = m.groups()
    h1, m1, h2, m2 = int(h1), int(m1), int(h2), int(m2)
    if meridiem.lower() == "pm":
        if h1 != 12:
            h1 += 12
        if h2 != 12:
            h2 += 12
    elif h1 == 12:
        h1 = 0
    return time(h1 % 24, m1), time(h2 % 24, m2)


def forwards(apps, schema_editor):
    GymClass = apps.get_model("schedules", "GymClass")
    for gc in GymClass.objects.all():
        start, end = _parse_block(gc.block)
        gc.start_time, gc.end_time = start, end
        gc.save(update_fields=["start_time", "end_time"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="gymclass",
            name="start_time",
            field=models.TimeField(default=time(8, 0), verbose_name="Hora de inicio"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="gymclass",
            name="end_time",
            field=models.TimeField(default=time(9, 0), verbose_name="Hora de fin"),
            preserve_default=False,
        ),
        migrations.RunPython(forwards, noop),
        migrations.RemoveField(
            model_name="gymclass",
            name="block",
        ),
        migrations.AlterModelOptions(
            name="gymclass",
            options={"ordering": ["day", "start_time"], "verbose_name": "Clase", "verbose_name_plural": "Clases"},
        ),
    ]
