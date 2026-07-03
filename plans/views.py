from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from configuration.utils import is_ajax, paginate
from services.models import Service
from .models import Plan
from .forms import PlanForm

TEMPLATE = "plans/plans.html"


class PlanList(LoginRequiredMixin, ListView):
    template_name = TEMPLATE
    context_object_name = "areas"
    paginate_by = 8

    def get_template_names(self):
        return ["plans/_results.html"] if is_ajax(self.request) else [TEMPLATE]

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        qs = Service.objects.prefetch_related("plans")
        if not q:
            return qs
        return qs.filter(Q(name__icontains=q) | Q(plans__name__icontains=q)).distinct()


class _Page(LoginRequiredMixin):
    model = Plan
    form_class = PlanForm
    template_name = TEMPLATE
    success_url = reverse_lazy("plans:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = paginate(self.request, Service.objects.prefetch_related("plans"), per_page=8)
        ctx["areas"] = page
        ctx["page_obj"] = page
        ctx["show_form"] = True
        return ctx

    def form_valid(self, form):
        if form.instance.pk is None:
            form.instance.created_by = self.request.user
        response = super().form_valid(form)
        if not self.object.included_services.exists():
            self.object.included_services.set([self.object.service])
        messages.success(self.request, "Plan guardado.")
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
        page = paginate(self.request, Service.objects.prefetch_related("plans"), per_page=8)
        ctx["areas"] = page
        ctx["page_obj"] = page
        ctx["show_delete"] = True
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Plan eliminado.")
        return super().form_valid(form)
