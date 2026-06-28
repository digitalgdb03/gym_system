from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Client, Membership
from .forms import ClientForm, MembershipForm, FreezeForm

TEMPLATE = "client/client.html"


class ClientList(LoginRequiredMixin, ListView):
    model = Client
    template_name = TEMPLATE
    context_object_name = "clients"

    def get_queryset(self):
        q = self.request.GET.get("q")
        qs = Client.objects.all()
        return qs.filter(Q(full_name__icontains=q) | Q(id_card__icontains=q)) if q else qs


class _Page(LoginRequiredMixin):
    model = Client
    form_class = ClientForm
    template_name = TEMPLATE
    success_url = reverse_lazy("client:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["clients"] = Client.objects.all()
        ctx["show_form"] = True
        return ctx


class ClientCreate(_Page, CreateView):
    pass


class ClientUpdate(_Page, UpdateView):
    pass


class ClientDelete(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = TEMPLATE
    success_url = reverse_lazy("client:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["clients"] = Client.objects.all()
        ctx["show_delete"] = True
        return ctx


def detail_context(client, **extra):
    ctx = {
        "client": client,
        "memberships": client.memberships.select_related("plan", "plan__service", "trainer"),
        "freeze": client.current_freeze,
        "payments": client.payments.select_related("plan")[:10],
    }
    ctx.update(extra)
    return ctx


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    action = request.GET.get("action")
    extra = {}
    if action == "membership":
        extra = {"membership_form": MembershipForm(), "show_membership": True}
    elif action == "freeze":
        extra = {"freeze_form": FreezeForm(), "show_freeze": True}
    return render(request, "client/detail.html", detail_context(client, **extra))


@login_required
def membership_add(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = MembershipForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        m = form.save(commit=False)
        m.client = client
        m.end_date = None
        m.save()
        messages.success(request, "Plan agregado.")
        return redirect("client:detail", pk=pk)
    return render(request, "client/detail.html",
                  detail_context(client, membership_form=form, show_membership=True))


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
    client = get_object_or_404(Client, pk=pk)
    form = FreezeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        client.freeze(form.cleaned_data["reason"], form.cleaned_data["days"])
        messages.success(request, "Membresía congelada.")
        return redirect("client:detail", pk=pk)
    return render(request, "client/detail.html",
                  detail_context(client, freeze_form=form, show_freeze=True))


@login_required
def client_unfreeze(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        client.unfreeze()
        messages.success(request, "Membresía reactivada.")
    return redirect("client:detail", pk=pk)
