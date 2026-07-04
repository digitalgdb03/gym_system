from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from configuration.utils import is_ajax, paginate
from user.permissions import FullAccessRequiredMixin
from .models import Service
from .forms import ServiceForm

TEMPLATE = "services/services.html"


class ServiceList(LoginRequiredMixin, FullAccessRequiredMixin, ListView):
    model = Service
    template_name = TEMPLATE
    context_object_name = "services"
    paginate_by = 15

    def get_template_names(self):
        return ["services/_results.html"] if is_ajax(self.request) else [TEMPLATE]

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        qs = Service.objects.order_by("-created_at")
        return qs.filter(name__icontains=q) if q else qs


class _Page(LoginRequiredMixin, FullAccessRequiredMixin):
    model = Service
    form_class = ServiceForm
    template_name = TEMPLATE
    success_url = reverse_lazy("services:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = paginate(self.request, Service.objects.order_by("-created_at"))
        ctx["services"] = page
        ctx["page_obj"] = page
        ctx["show_form"] = True
        return ctx

    def form_valid(self, form):
        if form.instance.pk is None:
            form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Área guardada.")
        return response


class ServiceCreate(_Page, CreateView):
    pass


class ServiceUpdate(_Page, UpdateView):
    pass


class ServiceDelete(LoginRequiredMixin, FullAccessRequiredMixin, DeleteView):
    model = Service
    template_name = TEMPLATE
    success_url = reverse_lazy("services:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = paginate(self.request, Service.objects.order_by("-created_at"))
        ctx["services"] = page
        ctx["page_obj"] = page
        ctx["show_delete"] = True
        return ctx

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "No se puede eliminar: el área tiene planes o clases asociados.")
            return redirect("services:list")
        messages.success(self.request, "Área eliminada.")
        return response
