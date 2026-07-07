from decimal import Decimal, ROUND_HALF_UP
from django import forms
from configuration.form_mixins import PlaceholderChoiceMixin
from configuration.models import GymConfig
from .models import Payment

CENTS = Decimal("0.01")


def _round2(value):
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


class PaymentForm(PlaceholderChoiceMixin, forms.ModelForm):
    start_date = forms.DateField(label="Inicio del plan", required=False,
                                 widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(label="Vencimiento del plan", required=False,
                               widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Payment
        fields = ["plan", "method", "amount_usd", "amount_bs", "is_custom"]

    field_order = ["plan", "method", "amount_usd", "amount_bs", "is_custom", "start_date", "end_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount_usd"].required = False
        self.fields["amount_bs"].required = False
        self.fields["amount_usd"].label = "Monto en USD"
        self.fields["amount_bs"].label = "Monto en Bs"
        self.fields["amount_usd"].help_text = "Solo para efectivo en USD. Vacío = tarifa del plan."
        self.fields["amount_bs"].help_text = "Para Bs, pago móvil, punto de venta o transferencia. Vacío = tarifa del plan."
        self.fields["is_custom"].help_text = ("Actívalo para modificar el monto a cancelar; "
                                              "los días de vigencia se calculan según ese monto.")
        self.fields["start_date"].help_text = "Se sugiere según el plan; edítala si hace falta."
        self.fields["end_date"].help_text = "Se sugiere según el plan; edítala si hace falta."

    def clean(self):
        cleaned = super().clean()
        start_date, end_date = cleaned.get("start_date"), cleaned.get("end_date")
        if start_date and end_date and end_date <= start_date:
            self.add_error("end_date", "El vencimiento debe ser posterior al inicio.")
        plan, method = cleaned.get("plan"), cleaned.get("method")
        if not (plan and method):
            return cleaned

        rate = GymConfig.load().bcv_rate
        amount_usd = cleaned.get("amount_usd")
        amount_bs = cleaned.get("amount_bs")

        if method in Payment.CASH_METHODS:
            if not amount_usd:
                amount_usd = plan.price(Payment.currency_for_method(method))
            if not rate:
                self.add_error("amount_usd", "No hay tasa BCV registrada; no se puede convertir a bolívares.")
            else:
                amount_bs = _round2(amount_usd * rate)
        else:
            if not rate:
                self.add_error("amount_bs", "No hay tasa BCV registrada; no se puede convertir a dólares.")
            else:
                if not amount_bs:
                    amount_bs = plan.price(Payment.currency_for_method(method)) * rate
                amount_bs = _round2(amount_bs)
                amount_usd = _round2(amount_bs / rate)

        cleaned["amount_usd"] = amount_usd
        cleaned["amount_bs"] = amount_bs
        return cleaned
