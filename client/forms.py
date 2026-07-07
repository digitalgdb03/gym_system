from django import forms
from configuration.form_mixins import PlaceholderChoiceMixin
from payments.forms import PaymentForm
from plans.models import Plan
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
            self.fields["status"].disabled = True

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

    field_order = ["plan", "trainer", "method", "amount_usd", "amount_bs", "is_custom",
                  "start_date", "end_date"]

    def clean(self):
        cleaned = super().clean()
        plan = cleaned.get("plan")
        if plan and plan.requires_trainer and not cleaned.get("trainer"):
            self.add_error("trainer", "Asigna un entrenador (Boxeo/MMA).")
        return cleaned


class AddPlanForm(InitialPaymentForm):
    """Agregar un plan adicional a un cliente que ya existe: mismo
    formulario y flujo de pago que el registro inicial, sin ofrecer
    planes que el cliente ya tiene asignados."""

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        if client is not None:
            existing = client.memberships.values_list("plan_id", flat=True)
            self.fields["plan"].queryset = self.fields["plan"].queryset.exclude(pk__in=existing)


class ChangePlanForm(PlaceholderChoiceMixin, forms.Form):
    """Cambia el plan de una membresía existente por otro que el cliente
    no tenga ya asignado. No es un pago nuevo: el monto y el vencimiento
    se recalculan según el plan elegido, sin tocar los demás planes del
    cliente."""
    plan = forms.ModelChoiceField(queryset=Plan.objects.all(), label="Nuevo plan")
    trainer = forms.ModelChoiceField(queryset=User.objects.filter(roles__contains=["INSTRUCTOR"]),
                                      required=False, label="Entrenador")

    def __init__(self, *args, membership=None, **kwargs):
        self.membership = membership
        super().__init__(*args, **kwargs)
        if membership is not None:
            existing = membership.client.memberships.values_list("plan_id", flat=True)
            self.fields["plan"].queryset = self.fields["plan"].queryset.exclude(pk__in=existing)

    def clean(self):
        cleaned = super().clean()
        plan = cleaned.get("plan")
        if plan and plan.requires_trainer and not cleaned.get("trainer"):
            self.add_error("trainer", "Asigna un entrenador (Boxeo/MMA).")
        return cleaned


class FreezeForm(forms.Form):
    """Congelación en días, con tope de Client.MAX_FREEZE_DAYS; no hay otras
    opciones de tipo (meses/indefinido)."""
    reason = forms.CharField(label="Motivo", max_length=160)
    days = forms.IntegerField(label="Cantidad de días", min_value=1, max_value=Client.MAX_FREEZE_DAYS)
