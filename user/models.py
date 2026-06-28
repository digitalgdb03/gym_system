from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN      = "ADMIN",      "Administrador"
        EMPLOYEE   = "EMPLOYEE",   "Empleado"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"

    full_name  = models.CharField("Nombre completo", max_length=120)
    role       = models.CharField("Rol", max_length=12, choices=Role.choices, default=Role.EMPLOYEE)
    id_card    = models.CharField("Cédula", max_length=20, blank=True)
    phone      = models.CharField("Teléfono", max_length=40, blank=True)
    detail     = models.CharField("Detalle / cargo", max_length=120, blank=True)
    discipline = models.ForeignKey("services.Service", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="instructors",
                                   verbose_name="Disciplina que enseña")

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.full_name or self.username

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR
