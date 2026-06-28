from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Service
from .forms import ServiceForm

TEMPLATE = "services/services.html"


class ServiceList(LoginRequiredMixin, ListView):
    model = Service
    template_name = TEMPLATE
    context_object_name = "services"


class _Page(LoginRequiredMixin):
    model = Service
    form_class = ServiceForm
    template_name = TEMPLATE
    success_url = reverse_lazy("services:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["services"] = Service.objects.all()
        ctx["show_form"] = True
        return ctx


class ServiceCreate(_Page, CreateView):
    pass


class ServiceUpdate(_Page, UpdateView):
    pass


class ServiceDelete(LoginRequiredMixin, DeleteView):
    model = Service
    template_name = TEMPLATE
    success_url = reverse_lazy("services:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["services"] = Service.objects.all()
        ctx["show_delete"] = True
        return ctx

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "No se puede eliminar: el área tiene planes o clases asociados.")
            return redirect("services:list")
