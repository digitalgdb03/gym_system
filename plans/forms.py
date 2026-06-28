from django import forms
from .models import Plan


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["area", "nombre", "duracion", "usd_bcv", "usd_divisas",
                  "incluye", "personalizado"]
        widgets = {
            "incluye": forms.CheckboxSelectMultiple,
        }
        help_texts = {
            "incluye": "Déjalo vacío para un plan simple; selecciona varias áreas para un combo.",
        }