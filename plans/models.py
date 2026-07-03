from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.db import models

from configuration.models import CreatedByModel


class Plan(CreatedByModel):
    class Duration(models.TextChoices):
        DAILY   = "DAILY",   "Diaria"
        WEEKLY  = "WEEKLY",  "Semanal"
        MONTHLY = "MONTHLY", "Mensual"

    class Currency(models.TextChoices):
        BCV  = "BCV",  "Bs (BCV)"
        CASH = "CASH", "Divisas ($)"

    service    = models.ForeignKey("services.Service", on_delete=models.PROTECT, related_name="plans")
    name       = models.CharField("Nombre", max_length=120, blank=True,
                                  help_text="Opcional · nómbralo solo en combos")
    duration   = models.CharField("Duración", max_length=10, choices=Duration.choices,
                                  default=Duration.MONTHLY)
    price_bcv  = models.DecimalField("Precio en dólares BCV", max_digits=8, decimal_places=2)
    price_cash = models.DecimalField("Precio en divisas/efectivo (USD)", max_digits=8, decimal_places=2)
    included_services = models.ManyToManyField("services.Service", blank=True,
                                               related_name="included_in",
                                               verbose_name="Áreas incluidas")
    is_custom  = models.BooleanField("Personalizado", default=False)
    is_active  = models.BooleanField("Activo", default=True)

    class Meta:
        ordering = ["service__name", "duration"]
        verbose_name = "Plan"
        verbose_name_plural = "Planes"

    def __str__(self):
        return self.label

    @property
    def label(self):
        return self.name or f"{self.service.name} · {self.get_duration_display()}"

    @property
    def requires_trainer(self):
        services = self.included_services.all() if self.pk and self.included_services.exists() else [self.service]
        return any(s.requires_trainer for s in services)

    def price(self, currency=Currency.BCV):
        return self.price_cash if currency == self.Currency.CASH else self.price_bcv

    def end_date_from(self, start):
        if self.duration == self.Duration.DAILY:
            return start + timedelta(days=1)
        if self.duration == self.Duration.WEEKLY:
            return start + timedelta(days=7)
        return start + relativedelta(months=1)
