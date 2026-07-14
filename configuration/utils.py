import json

from django.core.paginator import Paginator

PER_PAGE_CHOICES = [10, 25, 50, 100]


def paginate(request, queryset, per_page=10):
    """Pagina 'queryset'. El tamaño de página se puede sobrescribir con
    ?per_page=10|25|50|100, o ?per_page=all para verlos todos en una sola
    página (usado por el selector de la barra de paginación)."""
    raw = request.GET.get("per_page")
    if raw == "all":
        count = queryset.count() if hasattr(queryset, "count") else len(queryset)
        per_page = max(count, 1)
    elif raw and raw.isdigit() and int(raw) in PER_PAGE_CHOICES:
        per_page = int(raw)
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


class PerPageMixin:
    """Para ListView: permite sobrescribir paginate_by con ?per_page=
    10|25|50|100|all, mismo criterio que paginate() para el selector de la
    barra de paginación."""
    def get_paginate_by(self, queryset):
        raw = self.request.GET.get("per_page")
        if raw == "all":
            return max(queryset.count(), 1)
        if raw and raw.isdigit() and int(raw) in PER_PAGE_CHOICES:
            return int(raw)
        return self.paginate_by


def is_ajax(request):
    """True si el pedido viene del buscador automático (fetch), para
    devolver solo el fragmento de resultados sin recargar toda la página."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def plan_trainer_map_json():
    """{'<plan_id>': true/false} para que el JS muestre el entrenador solo
    cuando el plan seleccionado incluye clases dirigidas."""
    from plans.models import Plan
    plans = Plan.objects.select_related("service").prefetch_related("included_services")
    return json.dumps({str(p.pk): p.requires_trainer for p in plans})


def client_plans_json():
    """{'<client_id>': [plan_id, ...]} = planes ya asignados al cliente +
    todos los planes diarios activos, para filtrar el selector de planes
    en Pagos según el cliente elegido."""
    from client.models import Client
    from plans.models import Plan
    daily_ids = list(Plan.objects.filter(duration=Plan.Duration.DAILY, is_active=True)
                     .values_list("id", flat=True))
    data = {}
    for c in Client.objects.prefetch_related("memberships"):
        plan_ids = {m.plan_id for m in c.memberships.all()}
        plan_ids.update(daily_ids)
        data[str(c.pk)] = sorted(plan_ids)
    return json.dumps(data)


def plan_prices_json():
    """{'<plan_id>': {'bcv': precio, 'cash': precio, 'duration': 'DAILY'|
    'WEEKLY'|'MONTHLY'}} para autocompletar el monto y calcular la fecha de
    vencimiento sugerida según el plan y el método elegidos."""
    from plans.models import Plan
    return json.dumps({
        str(p.pk): {"bcv": str(p.price_bcv), "cash": str(p.price_cash), "duration": p.duration}
        for p in Plan.objects.all()
    })


def client_plan_end_dates_json():
    """{'<client_id>': {'<plan_id>': 'YYYY-MM-DD'}} = vencimiento actual de
    cada plan que ya tiene el cliente, para sugerir la fecha de inicio del
    nuevo período al renovar (mismo criterio que _renew_membership: si aún
    no vence, el nuevo período arranca donde termina el actual)."""
    from client.models import Client
    data = {}
    for c in Client.objects.prefetch_related("memberships"):
        data[str(c.pk)] = {
            str(m.plan_id): m.end_date.isoformat()
            for m in c.memberships.all() if m.end_date
        }
    return json.dumps(data)
