from django import forms
from .models import User


class StaffForm(forms.ModelForm):
    roles = forms.MultipleChoiceField(
        choices=User.Role.choices, widget=forms.CheckboxSelectMultiple,
        required=True, label="Roles")
    password1 = forms.CharField(
        label="Contraseña", required=False, widget=forms.PasswordInput,
        help_text="Con esta contraseña el usuario ingresará al sistema.")
    password2 = forms.CharField(
        label="Confirmar contraseña", required=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "full_name", "doc_type", "id_card", "email", "phone", "roles", "disciplines", "detail"]
        widgets = {"disciplines": forms.CheckboxSelectMultiple}
        help_texts = {"disciplines": "Selecciona una o varias disciplinas que enseña."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True
        self.fields["id_card"].required = True
        self.fields["doc_type"].required = True
        if self.instance.pk is None:
            self.fields["password1"].required = True
            self.fields["password2"].required = True
        else:
            self.fields["password1"].help_text = "Déjalo vacío para no cambiar la contraseña actual."
            self.fields["roles"].initial = self.instance.roles
            self.fields["id_card"].disabled = True
            self.fields["doc_type"].disabled = True

    def clean_id_card(self):
        return (self.cleaned_data.get("id_card") or "").replace(".", "").replace("-", "").strip()

    def clean(self):
        cleaned = super().clean()
        roles = cleaned.get("roles") or []
        if User.Role.INSTRUCTOR in roles and not cleaned.get("disciplines"):
            self.add_error("disciplines", "Selecciona al menos una disciplina que enseña.")

        id_card = cleaned.get("id_card")
        if id_card:
            qs = User.objects.filter(id_card=id_card)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("id_card", "Ya existe un usuario con esta cédula.")

        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif len(p1) < 6:
                self.add_error("password1", "La contraseña debe tener al menos 6 caracteres.")
        return cleaned


class ProfileForm(forms.ModelForm):
    """Formulario reducido para que cada usuario edite su propio perfil
    (sin poder tocar su rol, cédula o disciplinas)."""
    password1 = forms.CharField(
        label="Nueva contraseña", required=False, widget=forms.PasswordInput,
        help_text="Déjalo vacío para no cambiar tu contraseña actual.")
    password2 = forms.CharField(
        label="Confirmar nueva contraseña", required=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["full_name", "email", "phone"]

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif len(p1) < 6:
                self.add_error("password1", "La contraseña debe tener al menos 6 caracteres.")
        return cleaned
