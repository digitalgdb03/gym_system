from django import forms
from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["client", "plan", "method", "amount_usd"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount_usd"].required = False
        self.fields["amount_usd"].help_text = "Déjalo vacío para usar la tarifa del plan según el método."

    def clean(self):
        cleaned = super().clean()
        plan, method = cleaned.get("plan"), cleaned.get("method")
        if plan and method and not cleaned.get("amount_usd"):
            cleaned["amount_usd"] = plan.price(Payment.currency_for_method(method))
        return cleaned
