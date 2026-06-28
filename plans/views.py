from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from services.models import Service
from .models import Plan
from .forms import PlanForm

TEMPLATE = "plans/plans.html"


class PlanList(LoginRequiredMixin, ListView):
    template_name = TEMPLATE
    context_object_name = "areas"
    queryset = Service.objects.prefetch_related("plans")


class _Page(LoginRequiredMixin):
    model = Plan
    form_class = PlanForm
    template_name = TEMPLATE
    success_url = reverse_lazy("plans:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["areas"] = Service.objects.prefetch_related("plans")
        ctx["show_form"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.object.included_services.exists():
            self.object.included_services.set([self.object.service])
        return response


class PlanCreate(_Page, CreateView):
    pass


class PlanUpdate(_Page, UpdateView):
    pass


class PlanDelete(LoginRequiredMixin, DeleteView):
    model = Plan
    template_name = TEMPLATE
    success_url = reverse_lazy("plans:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["areas"] = Service.objects.prefetch_related("plans")
        ctx["show_delete"] = True
        return ctx
