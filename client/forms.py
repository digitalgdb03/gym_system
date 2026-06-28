from django import forms
from .models import Client, Membership


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "id_card", "email", "phone", "status", "health", "emergency_contact"]


class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ["plan", "start_date", "is_custom", "amount", "currency", "trainer"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"})}


class FreezeForm(forms.Form):
    reason = forms.CharField(label="Motivo", max_length=160)
    days   = forms.IntegerField(label="¿Cuántos días congelar?", min_value=1)
