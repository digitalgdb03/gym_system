from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView, View

from client.forms import ClientForm
from client.models import Client, Membership
from configuration.utils import is_ajax, paginate, client_plans_json, plan_prices_json
from .models import Payment
from .forms import PaymentForm
from attendance.models import Attendance

TEMPLATE = "payments/payments.html"


def _renew_membership(client, plan, user=None, is_custom=False, amount=None, currency=None):
    """El pago renueva el plan: extiende el vencimiento de la membresía
    (desde hoy si no tenía deuda de asistencia, o desde su vencimiento 
    si asistió al gimnasio estando moroso).
    Si el pago es personalizado, los días se calculan según el monto pagado
    en vez de usar la duración completa del plan."""
    
    membership = client.memberships.filter(plan=plan).order_by("-end_date").first()
    today = date.today()
    
    # NUEVA LÓGICA DE RENOVACIÓN
    if membership and membership.end_date:
        if membership.end_date > today:
            # Aún vigente: se suma a partir de su vencimiento futuro
            start = membership.end_date
        else:
            # Vencido: buscamos si asistió estando moroso
            has_attended = Attendance.objects.filter(
                client=client, 
                check_in__date__gt=membership.end_date
            ).exists()
            
            if has_attended:
                # Asistió: se cobra desde la fecha en que venció
                start = membership.end_date
            else:
                # No asistió: se perdona el tiempo y arranca desde hoy
                start = today
    else:
        # Cliente nuevo sin membresías previas
        start = today

    if is_custom and amount:
        days = plan.prorated_days(amount, currency, start)
        end = start + timedelta(days=days)
    else:
        end = plan.end_date_from(start)
        
    if membership:
        membership.end_date = end
        membership.save(update_fields=["end_date"])
    else:
        membership = Membership.objects.create(client=client, plan=plan, start_date=today, end_date=end,
                                                created_by=user)
    client.recompute_status()
    return membership


def _today_stats():
    today = timezone.localdate()
    payments = Payment.objects.filter(created_at__date=today)
    total = payments.aggregate(s=Sum("amount_usd"))["s"] or 0
    count = payments.count()
    return {"total": total, "count": count, "avg": total / count if count else 0}


def _list_ctx(request, q=""):
    payments = (Payment.objects.select_related("client", "plan", "plan__service")
                .order_by("-created_at"))
    q = (q or "").strip()
    if q:
        q_id = q.replace(".", "").replace("-", "")
        payments = payments.filter(Q(client__full_name__icontains=q) | Q(client__id_card__icontains=q_id))
    page = paginate(request, payments)
    return {"payments": page, "page_obj": page}


class PaymentList(LoginRequiredMixin, TemplateView):
    template_name = TEMPLATE

    def get(self, request, *args, **kwargs):
        if is_ajax(request):
            return render(request, "payments/_results.html", _list_ctx(request, request.GET.get("q")))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **_today_stats(),
                **_list_ctx(self.request, self.request.GET.get("q"))}


@login_required
def client_lookup(request):
    """Búsqueda de cliente por cédula o nombre para el formulario de Pagos
    (reemplaza el select por un buscador con registro inline si no existe)."""
    q = request.GET.get("q", "").strip()
    clients = []
    if q:
        q_id = q.replace(".", "").replace("-", "")
        clients = Client.objects.filter(
            Q(full_name__icontains=q) | Q(id_card__icontains=q_id)
        ).order_by("full_name")[:8]
    return render(request, "payments/_client_lookup.html", {"clients": clients, "q": q})


class PaymentCreate(LoginRequiredMixin, View):
    """Los pagos no se pueden editar ni eliminar: quedan como comprobante
    fijo del cobro (solo se puede registrar uno nuevo). El cliente se busca
    por cédula/nombre y, si no existe, se registra en el mismo formulario."""
    template_name = TEMPLATE

    def _ctx(self, form, client_form=None, client_search="", client_id=""):
        ctx = {**_today_stats(), **_list_ctx(self.request)}
        ctx["client_plans_json"] = client_plans_json()
        ctx["plan_prices_json"] = plan_prices_json()
        ctx["show_form"] = True
        ctx["form"] = form
        ctx["client_form"] = client_form or ClientForm()
        ctx["client_search"] = client_search
        ctx["client_id_value"] = client_id
        return ctx

    def get(self, request):
        return render(request, self.template_name, self._ctx(PaymentForm()))

    def post(self, request):
        form = PaymentForm(request.POST)
        client_id = request.POST.get("client_id", "").strip()
        client_search = request.POST.get("client_search", "").strip()
        client = None
        client_form = None

        if client_id:
            client = Client.objects.filter(pk=client_id).first()
            if not client:
                messages.error(request, "Selecciona un cliente válido de la lista.")
        else:
            client_form = ClientForm(request.POST)

        client_ready = client is not None or (client_form is not None and client_form.is_valid())

        if form.is_valid() and client_ready:
            with transaction.atomic():
                if client is None:
                    client = client_form.save(commit=False)
                    client.created_by = request.user
                    client.save()
                payment = form.save(commit=False)
                payment.client = client
                payment.created_by = request.user
                payment.save()
                _renew_membership(client, payment.plan, user=request.user, is_custom=payment.is_custom,
                                  amount=payment.amount_usd, currency=payment.currency)
            messages.success(request, "Pago guardado.")
            return redirect("payments:list")

        return render(request, self.template_name,
                      self._ctx(form, client_form, client_search, client_id))
