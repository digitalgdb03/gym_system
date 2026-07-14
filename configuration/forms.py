from django import forms
from .form_mixins import PersonFieldsValidationMixin
from .models import GymConfig


class GymInfoForm(PersonFieldsValidationMixin, forms.ModelForm):
    """Solo el teléfono usa la validación del mixin (nombre y RIF del
    gimnasio no son nombre/cédula de persona: sí admiten símbolos)."""
    class Meta:
        model = GymConfig
        fields = ["name", "tax_id", "address", "phone"]