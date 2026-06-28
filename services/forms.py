from django import forms
from .models import Servicio


class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ["nombre", "tipo", "color", "activo"]
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
        }