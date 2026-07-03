from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView

from .models import Payment
from .forms import PaymentForm

TEMPLATE = "payments/payments.html"


def _today_ctx():
    today = timezone.localdate()
    payments = (Payment.objects.filter(created_at__date=today)
                .select_related("client", "plan", "plan__service"))
    total = payments.aggregate(s=Sum("amount_usd"))["s"] or 0
    count = payments.count()
    return {"payments": payments, "total": total, "count": count,
            "avg": total / count if count else 0}


class PaymentList(LoginRequiredMixin, TemplateView):
    template_name = TEMPLATE

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **_today_ctx()}


class _Page(LoginRequiredMixin):
    model = Payment
    form_class = PaymentForm
    template_name = TEMPLATE
    success_url = reverse_lazy("payments:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_today_ctx())
        ctx["show_form"] = True
        return ctx


class PaymentCreate(_Page, CreateView):
    pass


class PaymentUpdate(_Page, UpdateView):
    pass


class PaymentDelete(LoginRequiredMixin, DeleteView):
    model = Payment
    template_name = TEMPLATE
    success_url = reverse_lazy("payments:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_today_ctx())
        ctx["show_delete"] = True
        return ctx
