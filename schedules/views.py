from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView

from .models import GymClass
from .forms import ClassForm

TEMPLATE = "schedules/schedules.html"


def _grid():
    classes = list(GymClass.objects.select_related("service", "instructor", "second_instructor"))
    grid = []
    for block in GymClass.BLOCKS:
        cells = []
        for value, _ in GymClass.Day.choices:
            items = [c for c in classes if c.block == block and c.day == value]
            cells.append({"day": value, "classes": items, "full": len(items) >= GymClass.MAX_PER_CELL})
        grid.append({"block": block, "cells": cells})
    return {"grid": grid, "days": GymClass.Day.choices}


class ScheduleList(LoginRequiredMixin, TemplateView):
    template_name = TEMPLATE

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **_grid()}


class _Page(LoginRequiredMixin):
    model = GymClass
    form_class = ClassForm
    template_name = TEMPLATE
    success_url = reverse_lazy("schedules:calendar")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_grid())
        ctx["show_form"] = True
        return ctx


class ClassCreate(_Page, CreateView):
    def get_initial(self):
        init = super().get_initial()
        for key in ("day", "block"):
            if key in self.request.GET:
                init[key] = self.request.GET[key]
        return init


class ClassUpdate(_Page, UpdateView):
    pass


class ClassDelete(LoginRequiredMixin, DeleteView):
    model = GymClass
    template_name = TEMPLATE
    success_url = reverse_lazy("schedules:calendar")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_grid())
        ctx["show_delete"] = True
        return ctx
