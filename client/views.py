from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, View, UpdateView, DeleteView

from configuration.utils import is_ajax, paginate, plan_trainer_map_json
from .models import Client, Membership, Freeze
from .forms import ClientForm, MembershipForm, FreezeForm

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


class ClientList(LoginRequiredMixin, ListView):
    model = Client
    template_name = TEMPLATE
    context_object_name = "clients"
    paginate_by = 15

    def get_template_names(self):
        return ["client/_results.html"] if is_ajax(self.request) else [TEMPLATE]

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        qs = Client.objects.prefetch_related(
            "memberships__plan__service", "memberships__trainer"
        )
        if not q:
            return qs
        q_id = q.replace(".", "").replace("-", "")
        return qs.filter(Q(full_name__icontains=q) | Q(id_card__icontains=q_id))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.GET.get("action") == "freeze" and self.request.GET.get("client"):
            target = get_object_or_404(Client, pk=self.request.GET["client"])
            ctx.update(_freeze_ctx(target, FreezeForm(), "list"))
        return ctx


class ClientCreate(LoginRequiredMixin, View):
    """Un cliente no puede registrarse sin al menos un plan: se crean
    Client y Membership juntos, en una sola transacción."""
    template_name = TEMPLATE

    def _ctx(self, form, membership_form):
        page = paginate(self.request, Client.objects.all())
        return {
            "clients": page,
            "page_obj": page,
            "show_form": True,
            "form": form,
            "membership_form": membership_form,
            "plan_trainer_map_json": plan_trainer_map_json(),
        }

    def get(self, request):
        return render(request, self.template_name,
                      self._ctx(ClientForm(), MembershipForm()))

    def post(self, request):
        form = ClientForm(request.POST)
        membership_form = MembershipForm(request.POST)
        if form.is_valid() and membership_form.is_valid():
            with transaction.atomic():
                client = form.save(commit=False)
                client.created_by = request.user
                client.save()
                m = membership_form.save(commit=False)
                m.client = client
                m.end_date = None
                m.created_by = request.user
                m.save()
            messages.success(request, "Cliente registrado.")
            return redirect("client:list")
        return render(request, self.template_name, self._ctx(form, membership_form))


class ClientUpdate(LoginRequiredMixin, UpdateView):
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
            page = paginate(self.request, Client.objects.all())
            ctx["clients"] = page
            ctx["page_obj"] = page
        return ctx

    def get_success_url(self):
        return _back_url(self._from(), self.object)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Cliente actualizado.")
        return response


class ClientDelete(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = TEMPLATE
    success_url = reverse_lazy("client:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = paginate(self.request, Client.objects.all())
        ctx["clients"] = page
        ctx["page_obj"] = page
        ctx["show_delete"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Cliente eliminado.")
        return response


def detail_context(client, **extra):
    ctx = {
        "client": client,
        "memberships": client.memberships.select_related("plan", "plan__service", "trainer"),
        "freeze": client.current_freeze,
        "payments": client.payments.select_related("plan").order_by("-created_at")[:10],
    }
    ctx.update(extra)
    return ctx


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    action = request.GET.get("action")
    extra = {}
    if action == "membership":
        extra = {"membership_form": MembershipForm(), "show_membership": True,
                 "plan_trainer_map_json": plan_trainer_map_json()}
    elif action == "freeze":
        extra = _freeze_ctx(client, FreezeForm(), "detail")
    return render(request, "client/detail.html", detail_context(client, **extra))


@login_required
def membership_add(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = MembershipForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        m = form.save(commit=False)
        m.client = client
        m.end_date = None
        m.created_by = request.user
        m.save()
        messages.success(request, "Plan agregado.")
        return redirect("client:detail", pk=pk)
    return render(request, "client/detail.html",
                  detail_context(client, membership_form=form, show_membership=True,
                                 plan_trainer_map_json=plan_trainer_map_json()))


@login_required
def membership_remove(request, pk):
    m = get_object_or_404(Membership, pk=pk)
    cid = m.client_id
    if request.method == "POST":
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
        kind = form.cleaned_data["kind"]
        amount = form.cleaned_data["days"] if kind == Freeze.Kind.DAYS else form.cleaned_data["months"]
        client.freeze(form.cleaned_data["reason"], kind, amount, user=request.user)
        messages.success(request, "Membresía congelada.")
        return redirect(_back_url(frm, client))

    if frm == "list":
        page = paginate(request, Client.objects.all())
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
