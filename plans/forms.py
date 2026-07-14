from django import forms
from configuration.form_mixins import AmountFieldsValidationMixin, PlaceholderChoiceMixin
from .models import Plan


class PlanForm(AmountFieldsValidationMixin, PlaceholderChoiceMixin, forms.ModelForm):
    amount_fields = ["price_bcv", "price_cash"]

    class Meta:
        model = Plan
        fields = ["service", "name", "duration", "price_bcv", "price_cash",
                  "included_services"]
        widgets = {"included_services": forms.CheckboxSelectMultiple}
        help_texts = {
            "included_services": "Déjalo vacío para un plan simple; selecciona varias áreas para un combo.",
        }
