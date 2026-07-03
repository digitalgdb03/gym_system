import re
from django.db import models
from django.utils import timezone

from configuration.models import CreatedByModel


def normalize_id(value):
    """V-25.481.230 -> 'v25481230' (quita puntos, guiones y espacios)."""
    return re.sub(r"[^0-9a-zA-Z]", "", value or "").lower()


class Attendance(CreatedByModel):
    client    = models.ForeignKey("client.Client", on_delete=models.CASCADE, related_name="attendances")
    check_in  = models.DateTimeField("Entrada", default=timezone.now)
    check_out = models.DateTimeField("Salida", null=True, blank=True)

    class Meta:
        ordering = ["-check_in"]
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"

    def __str__(self):
        return f"{self.client} · {self.check_in:%d/%m %I:%M %p}"

    @property
    def is_inside(self):
        return self.check_out is None
