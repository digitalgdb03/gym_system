from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .forms import GymConfigForm
from .models import ExchangeRate, GymConfig
from .rates import set_manual_rate, update_today_rate


class ConfigUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = GymConfigForm
    template_name = "configuration/config.html"
    success_url = reverse_lazy("configuration:edit")
    success_message = "Configuración guardada."

    def get_object(self, queryset=None):
        return GymConfig.load()

    def form_valid(self, form):
        response = super().form_valid(form)
        # Si editaron la tasa a mano, la registramos como MANUAL para hoy.
        if "bcv_rate" in form.changed_data:
            set_manual_rate(self.object.bcv_rate)
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rates"] = ExchangeRate.objects.all()[:12]
        return ctx


@login_required
def refresh_bcv(request):
    """Fuerza la consulta a la API del BCV y actualiza la tasa de hoy."""
    obj = update_today_rate(force=True)
    if obj and obj.source == ExchangeRate.Source.AUTO:
        messages.success(request, f"Tasa BCV actualizada: {obj.rate} Bs/USD.")
    else:
        messages.warning(request, "No se pudo conectar con el BCV. Ingresa la tasa manualmente abajo.")
    return redirect("configuration:edit")