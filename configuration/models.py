from datetime import timedelta

from django.db import models
from django.utils import timezone


class ExchangeRate(models.Model):
    """Registro de la tasa BCV por fecha efectiva. Fuente única.

    Regla de fin de semana (Art. 25 Ley del IVA): sábado y domingo usan la tasa
    del próximo lunes (que el BCV publica el viernes en la tarde). Por eso ambos
    se guardan/consultan bajo la fecha de ese lunes: sábado, domingo y lunes
    comparten una sola fila. El VIERNES conserva su propia tasa (no se toca).
    """

    # Hora aprox. de publicación del BCV. En días hábiles no se auto-actualiza
    # después de esta hora, para no capturar la tasa del próximo día hábil.
    BCV_PUBLISH_HOUR = 15

    class Source(models.TextChoices):
        AUTO   = "AUTO",   "Automática (BCV)"
        MANUAL = "MANUAL", "Manual"

    date       = models.DateField("Fecha efectiva", unique=True, default=timezone.localdate)
    rate       = models.DecimalField("Tasa (Bs/USD)", max_digits=12, decimal_places=2)
    source     = models.CharField("Origen", max_length=6, choices=Source.choices,
                                  default=Source.AUTO)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Tasa de cambio"
        verbose_name_plural = "Tasas de cambio"

    def __str__(self):
        return f"{self.date} · {self.rate} Bs ({self.get_source_display()})"

    # ---- Regla de fecha efectiva (SOLO desplaza sábado y domingo) ----
    @staticmethod
    def effective_date(for_date=None):
        """Fecha bajo la cual aplica la tasa del día 'for_date'.
        Sábado -> lunes (+2), domingo -> lunes (+1). Lunes a viernes: sin cambio."""
        d = for_date or timezone.localdate()
        wd = d.weekday()                 # lunes=0 ... viernes=4, sábado=5, domingo=6
        if wd == 5:
            return d + timedelta(days=2)
        if wd == 6:
            return d + timedelta(days=1)
        return d                          # el viernes se queda en viernes

    @classmethod
    def can_auto_update(cls, now=None):
        """En días hábiles solo se auto-actualiza antes de la publicación del BCV.
        En fin de semana siempre (la API ya devuelve la tasa del lunes)."""
        now = now or timezone.localtime()
        if now.weekday() >= 5:            # sábado/domingo
            return True
        return now.hour < cls.BCV_PUBLISH_HOUR

    @classmethod
    def for_today(cls):
        """La fila aplicable hoy (para sáb/dom, la del lunes). None si no existe."""
        return cls.objects.filter(date=cls.effective_date()).first()

    @classmethod
    def current(cls):
        """Tasa vigente: la aplicable hoy si existe; si no, la última guardada; si no, None."""
        obj = cls.for_today() or cls.objects.first()
        return obj.rate if obj else None


class GymConfig(models.Model):
    name    = models.CharField("Nombre", max_length=120, default="Zona Gym")
    tax_id  = models.CharField("RIF", max_length=20, blank=True)
    address = models.CharField("Dirección", max_length=200, blank=True)
    phone   = models.CharField("Teléfono", max_length=40, blank=True)

    class Meta:
        verbose_name = "Configuración"; verbose_name_plural = "Configuración"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1                       # fila única (singleton)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def bcv_rate(self):
        """La tasa ya no se guarda aquí; se lee de ExchangeRate (tabla diaria)."""
        return ExchangeRate.current()