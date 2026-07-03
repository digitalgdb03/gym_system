from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from configuration.utils import is_ajax, paginate
from .models import User
from .forms import StaffForm, ProfileForm

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
    paginate_by = 15

    def get_template_names(self):
        return ["user/_results.html"] if is_ajax(self.request) else [TEMPLATE]

    def get_queryset(self):
        qs = User.objects.filter(is_superuser=False).order_by("full_name")
        role = self.request.GET.get("role")
        if role in dict(User.Role.choices):
            qs = qs.filter(role=role)
        q = self.request.GET.get("q", "").strip()
        if q:
            q_id = q.replace(".", "").replace("-", "")
            qs = qs.filter(Q(full_name__icontains=q) | Q(id_card__icontains=q_id) | Q(email__icontains=q))
        return qs


class _Page(LoginRequiredMixin):
    model = User
    form_class = StaffForm
    template_name = TEMPLATE
    success_url = reverse_lazy("user:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = paginate(self.request, User.objects.filter(is_superuser=False).order_by("full_name"))
        ctx["staff"] = page
        ctx["page_obj"] = page
        ctx["show_form"] = True
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        if not obj.username:
            obj.username = _unique_username(obj.full_name)
            obj.created_by = self.request.user
        password = form.cleaned_data.get("password1")
        if password:
            obj.set_password(password)
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
        page = paginate(self.request, User.objects.order_by("full_name"))
        ctx["staff"] = page
        ctx["page_obj"] = page
        ctx["show_delete"] = True
        return ctx

    def form_valid(self, form):
        u = self.get_object()
        if u.classes_as_main.exists() or u.classes_as_second.exists():
            messages.error(self.request, "No se puede eliminar: el instructor tiene clases asignadas.")
            return redirect("user:list")
        response = super().form_valid(form)
        messages.success(self.request, "Usuario eliminado.")
        return response


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        password = form.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        user.save()
        if password:
            update_session_auth_hash(request, user)  # no cerrar la sesión al cambiar la contraseña
        messages.success(request, "Perfil actualizado.")
        return redirect("user:profile")
    return render(request, "user/profile.html", {"form": form})
