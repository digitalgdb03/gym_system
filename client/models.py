import calendar
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import models

from configuration.choices import DocType
from configuration.models import CreatedByModel
from plans.models import Plan


class Client(CreatedByModel):
    class Status(models.TextChoices):
        ACTIVE  = "ACTIVE",  "Activo"
        FROZEN  = "FROZEN",  "Congelado"
        OVERDUE = "OVERDUE", "Moroso"

    full_name         = models.CharField("Nombre completo", max_length=120)
    doc_type          = models.CharField("Tipo de documento", max_length=1,
                                        choices=DocType.choices, default=DocType.V)
    id_card           = models.CharField("Cédula", max_length=20)
    email             = models.EmailField("Correo", blank=True)
    phone             = models.CharField("Teléfono", max_length=40, blank=True)
    status            = models.CharField("Estado", max_length=10, choices=Status.choices,
                                         default=Status.ACTIVE)
    health            = models.CharField("Datos de salud", max_length=200, blank=True)
    emergency_contact = models.CharField("Contacto de emergencia", max_length=160, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        constraints = [
            models.UniqueConstraint(fields=["doc_type", "id_card"], name="client_unique_doc_id",
                                    violation_error_message="Ya existe un cliente con ese tipo y número de documento.")
        ]

    @property
    def full_id(self):
        return f"{self.doc_type}-{self.id_card}"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if self.id_card:
            self.id_card = self.id_card.replace(".", "").replace("-", "").strip()
        super().save(*args, **kwargs)

    @property
    def initials(self):
        return "".join(w[0] for w in self.full_name.split()[:2]).upper()

    @property
    def status_badge_class(self):
        return {self.Status.ACTIVE: "activo", self.Status.FROZEN: "congelado",
                self.Status.OVERDUE: "moroso"}[self.status]

    @property
    def current_freeze(self):
        return self.freezes.first() if self.status == self.Status.FROZEN else None
    
    @property
    def plans_summary(self):
        ms = list(self.memberships.all())
        if not ms:
            return ""
        if len(ms) == 1:
            return ms[0].plan.label                 # ej: "MMA · Mensual"
        names = [m.plan.service.name for m in ms]    # ej: ["Pesas", "Boxeo"]
        extra = f" +{len(names) - 2}" if len(names) > 2 else ""
        return ", ".join(names[:2]) + extra

    @property
    def trainers_summary(self):
        seen = []
        for m in self.memberships.all():
            if m.trainer:
                first = m.trainer.full_name.split()[0]
                if first not in seen:
                    seen.append(first)
        return ", ".join(seen)

    def freeze(self, reason, kind, amount=None, start=None, user=None):
        start = start or date.today()
        self.status = self.Status.FROZEN
        self.save(update_fields=["status"])

        if kind == Freeze.Kind.DAYS:
            days = amount
            end_date = start + timedelta(days=days)
        elif kind == Freeze.Kind.MONTHS:
            end_date = start + relativedelta(months=amount)
            days = (end_date - start).days
        else:
            days, end_date = None, None

        self.freezes.create(reason=reason, kind=kind, days=days,
                            start_date=start, end_date=end_date, created_by=user)
        if days:
            for m in self.memberships.all():
                if m.end_date:
                    m.end_date = m.end_date + timedelta(days=days)
                    m.save()
        return self

    def unfreeze(self):
        freeze = self.current_freeze
        if freeze and freeze.kind == Freeze.Kind.INDEFINITE:
            elapsed = (date.today() - freeze.start_date).days
            if elapsed:
                for m in self.memberships.all():
                    if m.end_date:
                        m.end_date = m.end_date + timedelta(days=elapsed)
                        m.save()
        self.status = self.Status.ACTIVE
        self.save(update_fields=["status"])
        return self


class Membership(CreatedByModel):
    client     = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="memberships")
    plan       = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="memberships")
    start_date = models.DateField("Inicio", default=date.today)
    end_date   = models.DateField("Vence", null=True, blank=True)
    trainer    = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True,
                                   limit_choices_to={"role": "INSTRUCTOR"},
                                   related_name="memberships_as_trainer", verbose_name="Entrenador")
    is_custom  = models.BooleanField("Personalizado", default=False)
    amount     = models.DecimalField("Monto pagado (USD)", max_digits=8, decimal_places=2,
                                     null=True, blank=True)
    currency   = models.CharField("Moneda", max_length=4, choices=Plan.Currency.choices,
                                  default=Plan.Currency.BCV)
    days       = models.PositiveIntegerField("Días", default=0)

    class Meta:
        verbose_name = "Membresía"
        verbose_name_plural = "Membresías"

    def __str__(self):
        return f"{self.client} · {self.plan.label}"

    def compute_end_date(self):
        if self.is_custom and self.amount:
            dim = calendar.monthrange(self.start_date.year, self.start_date.month)[1]
            per_day = self.plan.price(self.currency) / dim
            self.days = int(self.amount / per_day) if per_day else 0
            return self.start_date + timedelta(days=self.days)
        return self.plan.end_date_from(self.start_date)

    def clean(self):
        if self.plan_id and self.plan.requires_trainer and not self.trainer_id:
            raise ValidationError({"trainer": "Asigna un entrenador (Boxeo/MMA)."})
        if self.is_custom and not self.amount:
            raise ValidationError({"amount": "Indica el monto para calcular los días."})

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date is None:
            self.end_date = self.compute_end_date()
        super().save(*args, **kwargs)


class Freeze(CreatedByModel):
    class Kind(models.TextChoices):
        DAYS       = "DAYS",       "Días"
        MONTHS     = "MONTHS",     "Meses"
        INDEFINITE = "INDEFINITE", "Indefinido"

    client     = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="freezes")
    reason     = models.CharField("Motivo", max_length=160)
    kind       = models.CharField("Tipo", max_length=10, choices=Kind.choices, default=Kind.DAYS)
    days       = models.PositiveIntegerField("Días", null=True, blank=True)
    start_date = models.DateField("Desde")
    end_date   = models.DateField("Hasta", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Congelación"
        verbose_name_plural = "Congelaciones"
