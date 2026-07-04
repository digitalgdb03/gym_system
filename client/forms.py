from django import forms
from configuration.form_mixins import PlaceholderChoiceMixin
from payments.forms import PaymentForm
from user.models import User
from .models import Client, Membership, Freeze


class ClientForm(PlaceholderChoiceMixin, forms.ModelForm):
    """Al registrar un cliente nuevo no se pide el estado: siempre
    queda Activo por defecto. Al editar sí se puede ajustar."""
    class Meta:
        model = Client
        fields = ["full_name", "doc_type", "id_card", "email", "phone", "status", "health", "emergency_contact"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            del self.fields["status"]
        else:
            self.fields["id_card"].disabled = True
            self.fields["doc_type"].disabled = True

    def clean_id_card(self):
        return (self.cleaned_data.get("id_card") or "").replace(".", "").replace("-", "").strip()


class MembershipForm(PlaceholderChoiceMixin, forms.ModelForm):
    """La fecha de inicio es siempre hoy y el vencimiento se calcula
    automáticamente según el plan; por eso no se piden en el formulario."""
    class Meta:
        model = Membership
        fields = ["plan", "is_custom", "amount", "currency", "trainer"]


class InitialPaymentForm(PaymentForm):
    """El pago inicial de un cliente nuevo: mismo formulario y misma
    lógica que Pagos (sin 'client', que aún no existe), más el
    entrenador para áreas que lo requieren (Boxeo/MMA)."""
    trainer = forms.ModelChoiceField(queryset=User.objects.filter(roles__contains=["INSTRUCTOR"]),
                                      required=False, label="Entrenador")

    class Meta(PaymentForm.Meta):
        fields = ["plan", "trainer", "method", "amount_usd", "amount_bs", "is_custom"]

    field_order = ["plan", "trainer", "method", "amount_usd", "amount_bs", "is_custom"]

    def clean(self):
        cleaned = super().clean()
        plan = cleaned.get("plan")
        if plan and plan.requires_trainer and not cleaned.get("trainer"):
            self.add_error("trainer", "Asigna un entrenador (Boxeo/MMA).")
        return cleaned


class FreezeForm(forms.Form):
    reason = forms.CharField(label="Motivo", max_length=160)
    kind   = forms.ChoiceField(label="Tipo de congelación", choices=Freeze.Kind.choices,
                               widget=forms.RadioSelect, initial=Freeze.Kind.DAYS)
    days   = forms.IntegerField(label="Cantidad de días", min_value=1, required=False)
    months = forms.IntegerField(label="Cantidad de meses", min_value=1, required=False)

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        if kind == Freeze.Kind.DAYS and not cleaned.get("days"):
            self.add_error("days", "Indica la cantidad de días.")
        elif kind == Freeze.Kind.MONTHS and not cleaned.get("months"):
            self.add_error("months", "Indica la cantidad de meses.")
        return cleaned
