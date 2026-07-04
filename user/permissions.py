from functools import wraps

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class FullAccessRequiredMixin(UserPassesTestMixin):
    """Solo Super Admin (is_superuser) o Administrador (rol ADMIN) pasan.
    Usar junto a LoginRequiredMixin, colocado antes en la lista de bases."""

    def test_func(self):
        return self.request.user.has_full_access

    def handle_no_permission(self):
        raise PermissionDenied


def full_access_required(view_func):
    """Decorator para vistas basadas en función: exige rol ADMIN o superusuario.
    Debe usarse junto a @login_required, colocado después en la pila."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.has_full_access:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped
