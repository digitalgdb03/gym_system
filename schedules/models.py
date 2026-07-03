from django.core.exceptions import ValidationError
from django.db import models


class GymClass(models.Model):
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

    BLOCKS = [
        "8:40-10:30 am", "9:00-11:00 am", "2:40-3:50 pm",
        "6:00-7:00 pm", "7:00-8:00 pm", "8:00-9:00 pm", "9:00-10:00 pm",
    ]
    BLOCK_CHOICES = [(b, b) for b in BLOCKS]
    MAX_PER_CELL = 2

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
    day   = models.IntegerField("Día", choices=Day.choices)
    block = models.CharField("Bloque horario", max_length=20, choices=BLOCK_CHOICES)

    class Meta:
        ordering = ["day", "block"]
        verbose_name = "Clase"
        verbose_name_plural = "Clases"

    def __str__(self):
        return f"{self.service.name} · {self.get_day_display()} {self.block}"

    @property
    def instructor_names(self):
        names = [self.instructor.full_name.split()[0]]
        if self.second_instructor:
            names.append(self.second_instructor.full_name.split()[0])
        return " / ".join(names)

    def clean(self):
        if self.service_id and self.service.kind != "GUIDED":
            raise ValidationError({"service": "Solo las clases dirigidas se programan en el calendario."})

        siblings = GymClass.objects.filter(day=self.day, block=self.block)
        if self.pk:
            siblings = siblings.exclude(pk=self.pk)

        if siblings.count() >= self.MAX_PER_CELL:
            raise ValidationError(f"Cupo máximo ({self.MAX_PER_CELL}) en ese día y bloque.")

        if self.instructor_id and siblings.filter(
            models.Q(instructor=self.instructor) | models.Q(second_instructor=self.instructor)
        ).exists():
            raise ValidationError({"instructor": "Ese entrenador ya tiene una clase en ese bloque."})
