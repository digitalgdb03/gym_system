from django import forms
from .models import GymConfig


class GymConfigForm(forms.ModelForm):
    class Meta:
        model = GymConfig
        fields = ["nombre", "bcv", "rif", "direccion", "telefono"]