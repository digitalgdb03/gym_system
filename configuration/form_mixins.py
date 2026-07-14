import re

from django import forms

NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s'.-]+$")
PHONE_RE = re.compile(r"^[0-9]+$")


class PlaceholderChoiceMixin:
    """Cambia el "---------" por defecto de los selects de ForeignKey por
    un texto más claro ("Seleccione…")."""

    empty_choice_label = "Seleccione…"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = self.empty_choice_label


class PersonFieldsValidationMixin:
    """Valida los campos comunes de una persona (cliente o staff): el
    nombre solo admite letras, la cédula solo números (máx. 11 dígitos,
    sin puntos ni guiones) y el/los campo(s) de teléfono (definidos en
    phone_fields) solo números (máx. PHONE_MAX_DIGITS). Se aplica solo a
    los campos que el form realmente tenga.

    Además de la validación al guardar (clean_*), se marcan los widgets
    con data-only-letters / data-only-digits para que el script en
    base.html impida escribir caracteres inválidos en tiempo real."""

    ID_CARD_MAX_DIGITS = 11
    PHONE_MAX_DIGITS = 12
    phone_fields = ("phone",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "full_name" in self.fields:
            self.fields["full_name"].widget.attrs["data-only-letters"] = "1"
        if "id_card" in self.fields:
            self.fields["id_card"].widget.attrs["maxlength"] = self.ID_CARD_MAX_DIGITS
            self.fields["id_card"].widget.attrs["data-only-digits"] = "1"
            self.fields["id_card"].widget.attrs["inputmode"] = "numeric"
        for name in self.phone_fields:
            if name in self.fields:
                self.fields[name].widget.attrs["maxlength"] = self.PHONE_MAX_DIGITS
                self.fields[name].widget.attrs["data-only-digits"] = "1"
                self.fields[name].widget.attrs["inputmode"] = "numeric"

    def clean_full_name(self):
        value = (self.cleaned_data.get("full_name") or "").strip()
        if value and not NAME_RE.match(value):
            raise forms.ValidationError("El nombre solo puede contener letras.")
        return value

    def clean_id_card(self):
        value = (self.cleaned_data.get("id_card") or "").replace(".", "").replace("-", "").strip()
        if value:
            if not value.isdigit():
                raise forms.ValidationError("La cédula solo puede contener números.")
            if len(value) > self.ID_CARD_MAX_DIGITS:
                raise forms.ValidationError(f"La cédula debe tener máximo {self.ID_CARD_MAX_DIGITS} dígitos.")
        return value

    def clean(self):
        cleaned = super().clean()
        for name in self.phone_fields:
            if name not in self.fields:
                continue
            value = (cleaned.get(name) or "").strip()
            if not value:
                continue
            if not PHONE_RE.match(value):
                self.add_error(name, "Este campo solo puede contener números.")
            elif len(value) > self.PHONE_MAX_DIGITS:
                self.add_error(name, f"Máximo {self.PHONE_MAX_DIGITS} dígitos.")
        return cleaned


class AmountFieldsValidationMixin:
    """Marca los campos de monto (definidos en amount_fields) para que solo
    se puedan escribir números y un punto decimal, en tiempo real (vía
    data-only-amount, filtrado por el script en base.html) y usa un input
    de texto en vez de number para que ese filtrado funcione igual en todos
    los navegadores."""

    amount_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.amount_fields:
            field = self.fields.get(name)
            if field is None:
                continue
            field.widget = forms.TextInput(attrs=field.widget.attrs)
            field.widget.attrs["data-only-amount"] = "1"
            field.widget.attrs["inputmode"] = "decimal"
            field.widget.attrs["autocomplete"] = "off"
