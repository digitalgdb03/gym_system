from django.db import models
from configuration.models import CreatedByModel
from plans.models import Plan


class Payment(CreatedByModel):
    class Method(models.TextChoices):
        CASH_USD = "CASH_USD", "Efectivo (USD)"
        ZELLE    = "ZELLE",    "Zelle"
        BINANCE  = "BINANCE",  "Binance"
        CASH_BS  = "CASH_BS",  "Efectivo (Bs)"
        MOBILE   = "MOBILE",   "Pago Móvil"
        TRANSFER = "TRANSFER", "Transferencia"
        CARD     = "CARD",     "Punto de venta"

    # Métodos que se cobran y registran en USD/divisas (no en bolívares).
    CASH_METHODS = {Method.CASH_USD, Method.ZELLE, Method.BINANCE}

    client     = models.ForeignKey("client.Client", on_delete=models.CASCADE, related_name="payments")
    plan       = models.ForeignKey("plans.Plan", on_delete=models.PROTECT, related_name="payments")
    amount_usd = models.DecimalField("Monto (USD)", max_digits=8, decimal_places=2)
    amount_bs  = models.DecimalField("Monto (Bs)", max_digits=12, decimal_places=2, null=True, blank=True)
    method     = models.CharField("Método", max_length=10, choices=Method.choices, default=Method.MOBILE)
    currency   = models.CharField("Moneda", max_length=4, choices=Plan.Currency.choices,
                                  default=Plan.Currency.BCV)
    is_custom  = models.BooleanField("Personalizado", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"{self.client} · ${self.amount_usd}"

    @staticmethod
    def currency_for_method(method):
        return Plan.Currency.CASH if method in Payment.CASH_METHODS else Plan.Currency.BCV

    def save(self, *args, **kwargs):
        self.currency = self.currency_for_method(self.method)
        super().save(*args, **kwargs)
