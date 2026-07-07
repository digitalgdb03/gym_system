from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, View, UpdateView, DeleteView

from configuration.utils import is_ajax, paginate, plan_trainer_map_json, plan_prices_json, client_plan_end_dates_json
from payments.models import Payment
from payments.views import _renew_membership
from plans.models import Plan
from user.permissions import FullAccessRequiredMixin, full_access_required
from .models import Client, Membership, Freeze
from .forms import ClientForm, FreezeForm, InitialPaymentForm, AddPlanForm

TEMPLATE = "client/client.html"


def _back_url(frm, client):
    """A dónde volver tras una acción: la página desde la que se inició (lista o perfil)."""
    if frm == "detail":
        return reverse("client:detail", kwargs={"pk": client.pk})
    return reverse("client:list")


def _freeze_ctx(client, form, frm):
    return {
        "freeze_form": form,
        "show_freeze": True,
        "freeze_client": client,
        "freeze_from": frm,
        "freeze_close_url": _back_url(frm, client),
    }


def _membership_ctx(client, form, frm):
    return {
        "plan_form": form,
        "show_membership": True,
        "membership_client": client,
        "membership_from": frm,
        "membership_close_url": _back_url(frm, client),
        "plan_trainer_map_json": plan_trainer_map_json(),
        "plan_prices_json": plan_prices_json(),
        "client_plan_end_dates_json": client_plan_end_dates_json(),
    }


class ClientList(LoginRequiredMixin, ListView):
    model = Client
    template_name = TEMPLATE
    context_object_name = "clients"
    paginate_by = 15

    def get_template_names(self):
        return ["client/_results.html"] if is_ajax(self.request) else [TEMPLATE]

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        plan_id = self.request.GET.get("plan", "")
        qs = Client.objects.prefetch_related(
            "memberships__plan__service", "memberships__trainer"
        ).order_by("-created_at")
        if q:
            q_id = q.replace(".", "").replace("-", "")
            qs = qs.filter(Q(full_name__icontains=q) | Q(id_card__icontains=q_id))
        if status in dict(Client.Status.choices):
            qs = qs.filter(status=status)
        if plan_id:
            qs = qs.filter(memberships__plan_id=plan_id).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        for c in ctx["clients"]:
            c.recompute_status()
        ctx["status_choices"] = Client.Status.choices
        ctx["plan_choices"] = Plan.objects.select_related("service").order_by("service__name", "duration")
        ctx["selected_plan"] = self.request.GET.get("plan", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        if self.request.GET.get("action") == "freeze" and self.request.GET.get("client"):
            target = get_object_or_404(Client, pk=self.request.GET["client"])
            ctx.update(_freeze_ctx(target, FreezeForm(), "list"))
        if self.request.GET.get("action") == "membership" and self.request.GET.get("client"):
            target = get_object_or_404(Client, pk=self.request.GET["client"])
            ctx.update(_membership_ctx(target, AddPlanForm(client=target), "list"))
        return ctx


def register_client_with_payment(client_form, payment_form, user):
    """Crea Client + Payment + Membership en una sola transacción: el
    mismo flujo de registro inicial, reutilizado desde donde haga falta
    dar de alta un cliente nuevo (registro directo, Pagos, Asistencia)."""
    with transaction.atomic():
        client = client_form.save(commit=False)
        client.created_by = user
        client.save()

        plan = payment_form.cleaned_data["plan"]
        payment = Payment.objects.create(
            client=client, plan=plan,
            method=payment_form.cleaned_data["method"],
            amount_usd=payment_form.cleaned_data["amount_usd"],
            amount_bs=payment_form.cleaned_data["amount_bs"],
            is_custom=payment_form.cleaned_data["is_custom"],
            created_by=user,
        )
        membership = _renew_membership(
            client, plan, user=user, is_custom=payment.is_custom,
            amount=payment.amount_usd, currency=payment.currency,
            start_override=payment_form.cleaned_data.get("start_date"),
            end_override=payment_form.cleaned_data.get("end_date"),
        )
        trainer = payment_form.cleaned_data.get("trainer")
        if trainer:
            membership.trainer = trainer
            membership.save(update_fields=["trainer"])
    return client, membership


class ClientCreate(LoginRequiredMixin, View):
    """Un cliente no puede registrarse sin al menos un plan: se crean
    Client y Membership juntos, en una sola transacción, registrando
    el pago inicial con el mismo flujo que se usa en Pagos."""
    template_name = TEMPLATE

    def _ctx(self, form, payment_form):
        page = paginate(self.request, Client.objects.order_by("-created_at"))
        return {
            "clients": page,
            "page_obj": page,
            "show_form": True,
            "form": form,
            "membership_form": payment_form,
            "plan_trainer_map_json": plan_trainer_map_json(),
            "plan_prices_json": plan_prices_json(),
            "client_plan_end_dates_json": client_plan_end_dates_json(),
        }

    def get(self, request):
        return render(request, self.template_name,
                      self._ctx(ClientForm(), InitialPaymentForm()))

    def post(self, request):
        form = ClientForm(request.POST)
        payment_form = InitialPaymentForm(request.POST)
        if form.is_valid() and payment_form.is_valid():
            register_client_with_payment(form, payment_form, request.user)
            messages.success(request, "Cliente registrado.")
            return redirect("client:list")
        return render(request, self.template_name, self._ctx(form, payment_form))


class ClientUpdate(LoginRequiredMixin, FullAccessRequiredMixin, UpdateView):
    """Edita un cliente sin sacarlo de la página desde la que se abrió
    (lista o perfil): se queda ahí al cancelar, guardar o si hay error."""
    model = Client
    form_class = ClientForm

    def _from(self):
        return self.request.POST.get("from") or self.request.GET.get("from") or "list"

    def get_template_names(self):
        return ["client/detail.html"] if self._from() == "detail" else [TEMPLATE]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["show_form"] = True
        ctx["from_param"] = self._from()
        if self._from() == "detail":
            ctx.update(detail_context(self.object))
        else:
            page = paginate(self.request, Client.objects.order_by("-created_at"))
            ctx["clients"] = page
            ctx["page_obj"] = page
        return ctx

    def get_success_url(self):
        return _back_url(self._from(), self.object)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Cliente actualizado.")
        return response


class ClientDelete(LoginRequiredMixin, FullAccessRequiredMixin, DeleteView):
    model = Client
    template_name = TEMPLATE
    success_url = reverse_lazy("client:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = paginate(self.request, Client.objects.order_by("-created_at"))
        ctx["clients"] = page
        ctx["page_obj"] = page
        ctx["show_delete"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Cliente eliminado.")
        return response


def detail_context(client, **extra):
    memberships = list(client.memberships.select_related("plan", "plan__service", "trainer"))
    ctx = {
        "client": client,
        "memberships": memberships,
        "pending_memberships": [m for m in memberships if m.is_overdue],
        "freeze": client.current_freeze,
        "payments": client.payments.select_related("plan").order_by("-created_at")[:10],
    }
    ctx.update(extra)
    return ctx


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    client.recompute_status()
    action = request.GET.get("action")
    extra = {}
    if action == "membership":
        extra = _membership_ctx(client, AddPlanForm(client=client), "detail")
    elif action == "freeze":
        extra = _freeze_ctx(client, FreezeForm(), "detail")
    return render(request, "client/detail.html", detail_context(client, **extra))


@login_required
@full_access_required
def membership_add(request, pk):
    """Agrega un plan a un cliente que ya existe: registra el pago y
    renueva la membresía con el mismo flujo que un pago normal."""
    client = get_object_or_404(Client, pk=pk)
    frm = request.POST.get("from") or request.GET.get("from") or "detail"
    form = AddPlanForm(request.POST or None, client=client)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            plan = form.cleaned_data["plan"]
            payment = Payment.objects.create(
                client=client, plan=plan,
                method=form.cleaned_data["method"],
                amount_usd=form.cleaned_data["amount_usd"],
                amount_bs=form.cleaned_data["amount_bs"],
                is_custom=form.cleaned_data["is_custom"],
                created_by=request.user,
            )
            membership = _renew_membership(
                client, plan, user=request.user, is_custom=payment.is_custom,
                amount=payment.amount_usd, currency=payment.currency,
                start_override=form.cleaned_data.get("start_date"),
                end_override=form.cleaned_data.get("end_date"),
            )
            trainer = form.cleaned_data.get("trainer")
            if trainer:
                membership.trainer = trainer
                membership.save(update_fields=["trainer"])
        messages.success(request, "Plan agregado.")
        return redirect(_back_url(frm, client))

    if frm == "list":
        page = paginate(request, Client.objects.order_by("-created_at"))
        ctx = {"clients": page, "page_obj": page}
        ctx.update(_membership_ctx(client, form, "list"))
        return render(request, TEMPLATE, ctx)
    return render(request, "client/detail.html",
                  detail_context(client, **_membership_ctx(client, form, "detail")))


@login_required
@full_access_required
def membership_remove(request, pk):
    m = get_object_or_404(Membership, pk=pk)
    cid = m.client_id
    if request.method == "POST":
        if m.client.memberships.count() <= 1:
            messages.error(request, "El cliente debe tener al menos un plan asignado.")
        else:
            m.delete()
            messages.success(request, "Plan eliminado.")
    return redirect("client:detail", pk=cid)


@login_required
def client_freeze(request, pk):
    """Congela la membresía sin sacar al usuario de la página desde la
    que se abrió el formulario (lista o perfil)."""
    client = get_object_or_404(Client, pk=pk)
    frm = request.POST.get("from") or request.GET.get("from") or "detail"
    form = FreezeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        client.freeze(form.cleaned_data["reason"], Freeze.Kind.DAYS, form.cleaned_data["days"], user=request.user)
        messages.success(request, "Membresía congelada.")
        return redirect(_back_url(frm, client))

    if frm == "list":
        page = paginate(request, Client.objects.order_by("-created_at"))
        ctx = {"clients": page, "page_obj": page}
        ctx.update(_freeze_ctx(client, form, "list"))
        return render(request, TEMPLATE, ctx)
    return render(request, "client/detail.html",
                  detail_context(client, **_freeze_ctx(client, form, "detail")))


@login_required
def client_unfreeze(request, pk):
    """Reactiva la membresía y vuelve a la página desde la que se pidió
    (lista o perfil), sin forzar una navegación al perfil."""
    client = get_object_or_404(Client, pk=pk)
    frm = request.POST.get("from") or request.GET.get("from") or "detail"
    if request.method == "POST":
        client.unfreeze()
        messages.success(request, "Membresía reactivada.")
    return redirect(_back_url(frm, client))
