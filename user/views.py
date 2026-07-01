from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import User
from .forms import StaffForm

TEMPLATE = "user/users.html"


def _unique_username(base):
    base = slugify(base) or "staff"
    username, i = base, 1
    while User.objects.filter(username=username).exists():
        i += 1
        username = f"{base}{i}"
    return username


class StaffList(LoginRequiredMixin, ListView):
    model = User
    template_name = TEMPLATE
    context_object_name = "staff"

    def get_queryset(self):
        qs = User.objects.filter(is_superuser=False).order_by("full_name")
        role = self.request.GET.get("role")
        return qs.filter(role=role) if role in dict(User.Role.choices) else qs


class _Page(LoginRequiredMixin):
    model = User
    form_class = StaffForm
    template_name = TEMPLATE
    success_url = reverse_lazy("user:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["staff"] = User.objects.filter(is_superuser=False).order_by("full_name")
        ctx["show_form"] = True
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        creating = obj.pk is None
        if not obj.username:
            obj.username = _unique_username(obj.full_name)
        if creating:
            obj.set_unusable_password()
        obj.save()
        form.save_m2m()
        messages.success(self.request, "Usuario guardado.")
        return redirect(self.success_url)


class StaffCreate(_Page, CreateView):
    pass


class StaffUpdate(_Page, UpdateView):
    pass


class StaffDelete(LoginRequiredMixin, DeleteView):
    model = User
    template_name = TEMPLATE
    success_url = reverse_lazy("user:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["staff"] = User.objects.order_by("full_name")
        ctx["show_delete"] = True
        return ctx

    def form_valid(self, form):
        u = self.get_object()
        if u.classes_as_main.exists() or u.classes_as_second.exists():
            messages.error(self.request, "No se puede eliminar: el instructor tiene clases asignadas.")
            return redirect("user:list")
        return super().form_valid(form)
