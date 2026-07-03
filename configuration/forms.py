from django import forms
from .models import GymConfig


class GymInfoForm(forms.ModelForm):
    class Meta:
        model = GymConfig
        fields = ["name", "tax_id", "address", "phone"]