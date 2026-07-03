from django import forms


class PlaceholderChoiceMixin:
    """Cambia el "---------" por defecto de los selects de ForeignKey por
    un texto más claro ("Seleccione…")."""

    empty_choice_label = "Seleccione…"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = self.empty_choice_label
