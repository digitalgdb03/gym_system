from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.db.models import ProtectedError
from .models import Servicio
from .forms import ServicioForm


class ServicioListView(LoginRequiredMixin, ListView):
    model = Servicio
    template_name = "services/list.html"
    context_object_name = "servicios"



class ServicioCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Servicio
    form_class = ServicioForm
    template_name = "services/form.html"
    success_url = reverse_lazy("services:list")
    success_message = "Servicio creado correctamente."


class ServicioUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Servicio
    form_class = ServicioForm
    template_name = "services/form.html"
    success_url = reverse_lazy("services:list")
    success_message = "Servicio actualizado."


class ServicioDeleteView(LoginRequiredMixin, DeleteView):
    model = Servicio
    template_name = "services/confirm_delete.html"
    success_url = reverse_lazy("services:list")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "No se puede eliminar: el área tiene planes o clases asociados.")
            return redirect("services:list")
