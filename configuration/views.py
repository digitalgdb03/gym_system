from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .models import GymConfig
from .forms import GymConfigForm


class ConfigUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = GymConfigForm
    template_name = "configuration/config.html"
    success_url = reverse_lazy("configuration:edit")
    success_message = "Configuración guardada."

    def get_object(self, queryset=None):
        return GymConfig.load()