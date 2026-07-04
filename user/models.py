from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models

from configuration.choices import DocType
from configuration.models import CreatedByModel


class User(AbstractUser, CreatedByModel):
    class Role(models.TextChoices):
        ADMIN      = "ADMIN",      "Administrador"
        EMPLOYEE   = "EMPLOYEE",   "Empleado"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"

    full_name  = models.CharField("Nombre completo", max_length=120)
    roles      = ArrayField(models.CharField(max_length=12, choices=Role.choices),
                            default=list, blank=True, verbose_name="Roles")
    doc_type   = models.CharField("Tipo de documento", max_length=1,
                                  choices=DocType.choices, default=DocType.V)
    id_card    = models.CharField("Cédula", max_length=20, blank=True)
    phone      = models.CharField("Teléfono", max_length=40, blank=True)
    detail     = models.CharField("Detalle / cargo", max_length=120, blank=True)
    disciplines = models.ManyToManyField("services.Service", blank=True,
                                         related_name="instructors",
                                         verbose_name="Disciplinas que enseña")

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.full_name or self.username

    @property
    def is_instructor(self):
        return self.Role.INSTRUCTOR in self.roles

    @property
    def has_full_access(self):
        """Super admin (is_superuser) y Administrador (rol ADMIN) ven y hacen todo."""
        return self.is_superuser or self.Role.ADMIN in self.roles

    @property
    def roles_label(self):
        labels = dict(self.Role.choices)
        return ", ".join(labels.get(r, r) for r in self.roles)

    @property
    def roles_display_list(self):
        labels = dict(self.Role.choices)
        return [(r, labels.get(r, r)) for r in self.roles]

    @property
    def full_id(self):
        return f"{self.doc_type}-{self.id_card}" if self.id_card else ""
