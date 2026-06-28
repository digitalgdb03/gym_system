from decimal import Decimal
from django.db import models


class GymConfig(models.Model):
    name     = models.CharField("Nombre", max_length=120, default="Zona Gym")
    bcv_rate = models.DecimalField("Tasa BCV (Bs/USD)", max_digits=10, decimal_places=2,
                                   default=Decimal("40.00"))
    tax_id   = models.CharField("RIF", max_length=20, blank=True)
    address  = models.CharField("Dirección", max_length=200, blank=True)
    phone    = models.CharField("Teléfono", max_length=40, blank=True)

    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuración"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1                       # fila única (singleton)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
