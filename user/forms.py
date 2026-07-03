from django import forms
from .models import User


class StaffForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "id_card", "email", "phone", "role", "discipline", "detail"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == User.Role.INSTRUCTOR and not cleaned.get("discipline"):
            self.add_error("discipline", "Selecciona la disciplina que enseña.")
        return cleaned
