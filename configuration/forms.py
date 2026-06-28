from django import forms
from .models import GymConfig


class GymConfigForm(forms.ModelForm):
    class Meta:
        model = GymConfig
        fields = ["name", "bcv_rate", "tax_id", "address", "phone"]
