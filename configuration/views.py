from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import GymInfoForm
from .models import ExchangeRate, GymConfig
from .rates import set_manual_rate, update_today_rate


@login_required
def edit(request):
    """Página de Configuración: datos del gimnasio + tasa manual + historial."""
    cfg = GymConfig.load()
    if request.method == "POST":                      # guardar datos del gimnasio
        form = GymInfoForm(request.POST, instance=cfg)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos del gimnasio guardados.")
            return redirect("configuration:edit")
    else:
        form = GymInfoForm(instance=cfg)

    last = ExchangeRate.objects.first()
    ctx = {
        "form": form,
        "today_rate": ExchangeRate.for_today(),
        "suggested_rate": last.rate if last else "",
        "rates": ExchangeRate.objects.all()[:12],
    }
    return render(request, "configuration/config.html", ctx)


@login_required
def save_rate(request):
    """Guarda la tasa de HOY a mano. Bloquea si ya existe una para hoy."""
    if ExchangeRate.for_today():
        messages.warning(request, "Ya hay una tasa registrada para hoy.")
        return redirect("configuration:edit")
    if request.method == "POST":
        raw = request.POST.get("rate", "").replace(",", ".").strip()
        try:
            rate = Decimal(raw)
            if rate <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            messages.error(request, "Ingresa una tasa válida.")
            return redirect("configuration:edit")
        set_manual_rate(rate)
        messages.success(request, f"Tasa guardada: {rate} Bs/USD.")
    return redirect("configuration:edit")


@login_required
def refresh_bcv(request):
    """Consulta la API del BCV. Bloquea si ya existe una tasa para hoy."""
    if ExchangeRate.for_today():
        messages.warning(request, "Ya hay una tasa registrada para hoy.")
        return redirect("configuration:edit")
    obj = update_today_rate(force=True)
    if obj:
        messages.success(request, f"Tasa BCV actualizada: {obj.rate} Bs/USD.")
    else:
        messages.warning(request, "No se pudo conectar con el BCV. Ingresa la tasa manualmente.")
    return redirect("configuration:edit")