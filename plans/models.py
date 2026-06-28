from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.db import models


class Plan(models.Model):
    class Duracion(models.TextChoices):
        DIARIA  = "Diaria",  "Diaria"
        SEMANAL = "Semanal", "Semanal"
        MENSUAL = "Mensual", "Mensual"

    area     = models.ForeignKey("services.Servicio", on_delete=models.PROTECT,
                                 related_name="planes")
    nombre   = models.CharField(max_length=120, blank=True,
                                help_text="Opcional · nómbralo solo en combos")
    duracion = models.CharField(max_length=10, choices=Duracion.choices,
                                default=Duracion.MENSUAL)
    usd_bcv     = models.DecimalField("Precio BCV (USD)", max_digits=8, decimal_places=2)
    usd_divisas = models.DecimalField("Precio Divisas (USD)", max_digits=8, decimal_places=2)
    incluye  = models.ManyToManyField("services.Servicio", blank=True,
                                      related_name="incluido_en",
                                      help_text="Áreas que cubre (combos)")
    personalizado = models.BooleanField(default=False)
    activo        = models.BooleanField(default=True)

    class Meta:
        ordering = ["area__nombre", "duracion"]
        verbose_name = "Plan"
        verbose_name_plural = "Planes"

    def __str__(self):
        return self.etiqueta

    @property
    def etiqueta(self):
        return self.nombre or f"{self.area.nombre} · {self.duracion}"

    @property
    def requiere_entrenador(self):
        areas = self.incluye.all() if self.pk and self.incluye.exists() else [self.area]
        return any(a.requiere_entrenador for a in areas)

    def precio(self, moneda="BCV"):
        return self.usd_divisas if moneda == "Divisas" else self.usd_bcv

    def vence_desde(self, inicio):
        if self.duracion == self.Duracion.DIARIA:
            return inicio + timedelta(days=1)
        if self.duracion == self.Duracion.SEMANAL:
            return inicio + timedelta(days=7)
        return inicio + relativedelta(months=1)