from datetime import time
from django.db import migrations

OPEN_MIN = 5 * 60
CLOSE_MIN = 22 * 60


def _round_to_half_hour(t):
    total = t.hour * 60 + t.minute
    rounded = round(total / 30) * 30
    rounded = max(OPEN_MIN, min(CLOSE_MIN, rounded))
    return time(rounded // 60, rounded % 60)


def forwards(apps, schema_editor):
    GymClass = apps.get_model("schedules", "GymClass")
    for gc in GymClass.objects.all():
        start = _round_to_half_hour(gc.start_time)
        end = _round_to_half_hour(gc.end_time)
        if end <= start:
            end = time(min(21, start.hour + 1) if start.hour < 21 else 22, 30 if start.hour < 21 else 0)
        if start != gc.start_time or end != gc.end_time:
            gc.start_time, gc.end_time = start, end
            gc.save(update_fields=["start_time", "end_time"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0003_start_end_time"),
    ]

    operations = [
        migrations.RunPython(forwards, noop),
    ]
