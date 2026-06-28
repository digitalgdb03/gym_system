from django.db import models

class Service(models.Model):
    class Kind(models.TextChoices):
        OPEN   = "OPEN",   "Acceso libre"
        GUIDED = "GUIDED", "Clase dirigida"
        MIXED  = "MIXED",  "Mixto / combos"

    name  = models.CharField(max_length=80, unique=True)
    color = models.CharField(max_length=7, default="#343959")
    kind  = models.CharField(max_length=10, choices=Kind.choices, default=Kind.OPEN)
    requires_trainer = models.BooleanField(default=False,
        help_text="Marca Boxeo/MMA: exige asignar entrenador en la membresía")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]; verbose_name = "Servicio"; verbose_name_plural = "Servicios"

    def __str__(self): return self.name
