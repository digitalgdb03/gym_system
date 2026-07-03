from django.db import models


class DocType(models.TextChoices):
    V = "V", "V - Venezolano"
    E = "E", "E - Extranjero"
    J = "J", "J - Jurídico"
    P = "P", "P - Pasaporte"
