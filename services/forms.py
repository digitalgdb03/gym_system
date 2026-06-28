from django import forms
from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "kind", "color", "requires_trainer", "is_active"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}
