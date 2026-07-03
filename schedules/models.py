from datetime import time
from django.core.exceptions import ValidationError
from django.db import models

from configuration.models import CreatedByModel


class GymClass(CreatedByModel):
    class Kind(models.TextChoices):
        FIXED  = "FIXED",  "Fija"
        CUSTOM = "CUSTOM", "Personalizada"

    class Day(models.IntegerChoices):
        MON = 0, "Lunes"
        TUE = 1, "Martes"
        WED = 2, "Miércoles"
        THU = 3, "Jueves"
        FRI = 4, "Viernes"
        SAT = 5, "Sábado"

    MAX_PER_CELL = 2
    OPEN_TIME  = time(5, 0)
    CLOSE_TIME = time(22, 0)

    service           = models.ForeignKey("services.Service", on_delete=models.PROTECT,
                                           related_name="classes",
                                           limit_choices_to={"kind": "GUIDED"},
                                           verbose_name="Clase dirigida")
    kind              = models.CharField("Tipo", max_length=10, choices=Kind.choices, default=Kind.FIXED)
    instructor        = models.ForeignKey("user.User", on_delete=models.PROTECT,
                                           related_name="classes_as_main",
                                           limit_choices_to={"role": "INSTRUCTOR"},
                                           verbose_name="Entrenador")
    second_instructor = models.ForeignKey("user.User", on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name="classes_as_second",
                                           limit_choices_to={"role": "INSTRUCTOR"},
                                           verbose_name="Segundo entrenador")
    day        = models.IntegerField("Día", choices=Day.choices)
    start_time = models.TimeField("Hora de inicio")
    end_time   = models.TimeField("Hora de fin")

    class Meta:
        ordering = ["day", "start_time"]
        verbose_name = "Clase"
        verbose_name_plural = "Clases"

    def __str__(self):
        return f"{self.service.name} · {self.get_day_display()} {self.block_label}"

    @property
    def block_label(self):
        if not (self.start_time and self.end_time):
            return ""
        return f"{self.start_time:%I:%M %p} - {self.end_time:%I:%M %p}".replace("AM", "am").replace("PM", "pm")

    @property
    def instructor_names(self):
        names = [self.instructor.full_name.split()[0]]
        if self.second_instructor:
            names.append(self.second_instructor.full_name.split()[0])
        return " / ".join(names)

    def clean(self):
        if self.service_id and self.service.kind != "GUIDED":
            raise ValidationError({"service": "Solo las clases dirigidas se programan en el calendario."})

        if self.start_time and self.end_time:
            if self.start_time < self.OPEN_TIME or self.end_time > self.CLOSE_TIME:
                raise ValidationError("El horario debe estar entre las 5:00 am y las 10:00 pm.")
            if self.end_time <= self.start_time:
                raise ValidationError({"end_time": "La hora de fin debe ser posterior a la hora de inicio."})

        if self.day is None or not (self.start_time and self.end_time):
            return

        siblings = GymClass.objects.filter(day=self.day)
        if self.pk:
            siblings = siblings.exclude(pk=self.pk)
        overlapping = siblings.filter(start_time__lt=self.end_time, end_time__gt=self.start_time)

        if overlapping.count() >= self.MAX_PER_CELL:
            raise ValidationError(f"Cupo máximo ({self.MAX_PER_CELL}) de clases simultáneas en ese horario.")

        if self.instructor_id and overlapping.filter(
            models.Q(instructor=self.instructor) | models.Q(second_instructor=self.instructor)
        ).exists():
            raise ValidationError({"instructor": "Ese entrenador ya tiene una clase que se cruza con ese horario."})
