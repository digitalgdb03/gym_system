import json

from django.core.paginator import Paginator


def paginate(request, queryset, per_page=10):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


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
