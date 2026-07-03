from django import forms
from configuration.form_mixins import PlaceholderChoiceMixin
from .models import Plan


class PlanForm(PlaceholderChoiceMixin, forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["service", "name", "duration", "price_bcv", "price_cash",
                  "included_services", "is_custom"]
        widgets = {"included_services": forms.CheckboxSelectMultiple}
        help_texts = {
            "included_services": "Déjalo vacío para un plan simple; selecciona varias áreas para un combo.",
        }
