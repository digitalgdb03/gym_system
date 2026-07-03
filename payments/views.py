from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, CreateView

from client.models import Membership
from configuration.utils import is_ajax, paginate
from .models import Payment
from .forms import PaymentForm

TEMPLATE = "payments/payments.html"


def _renew_membership(client, plan, user=None):
    """El pago renueva el plan: extiende el vencimiento de la membresía
    (desde hoy si ya venció, o desde su vencimiento si aún está vigente)."""
    membership = client.memberships.filter(plan=plan).order_by("-end_date").first()
    today = date.today()
    start = membership.end_date if membership and membership.end_date and membership.end_date > today else today
    end = plan.end_date_from(start)
    if membership:
        membership.end_date = end
        membership.save(update_fields=["end_date"])
    else:
        membership = Membership.objects.create(client=client, plan=plan, start_date=today, end_date=end,
                                                created_by=user)
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


class _Page(LoginRequiredMixin):
    model = Payment
    form_class = PaymentForm
    template_name = TEMPLATE
    success_url = reverse_lazy("payments:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_today_stats())
        ctx.update(_list_ctx(self.request))
        ctx["show_form"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Pago guardado.")
        return response


class PaymentCreate(_Page, CreateView):
    """Los pagos no se pueden editar ni eliminar: quedan como
    comprobante fijo del cobro (solo se puede registrar uno nuevo)."""
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        _renew_membership(self.object.client, self.object.plan, user=self.request.user)
        return response
