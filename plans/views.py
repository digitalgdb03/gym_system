from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView

from services.models import Servicio
from .models import Plan
from .forms import PlanForm


@login_required
def plan_list(request):
    # Agrupado por área, como en la pantalla del demo
    areas = Servicio.objects.prefetch_related("planes").order_by("nombre")
    return render(request, "plans/list.html", {"areas": areas})


class _PlanFormMixin(LoginRequiredMixin, SuccessMessageMixin):
    model = Plan
    form_class = PlanForm
    template_name = "plans/form.html"
    success_url = reverse_lazy("plans:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        # Si no marcó áreas en un combo, "incluye" = su propia área
        if not self.object.incluye.exists():
            self.object.incluye.set([self.object.area])
        return response


class PlanCreateView(_PlanFormMixin, CreateView):
    success_message = "Plan creado."


class PlanUpdateView(_PlanFormMixin, UpdateView):
    success_message = "Plan actualizado."


class PlanDeleteView(LoginRequiredMixin, DeleteView):
    model = Plan
    template_name = "plans/confirm_delete.html"
    success_url = reverse_lazy("plans:list")
