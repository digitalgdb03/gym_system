from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView

from user.permissions import FullAccessRequiredMixin
from .models import GymClass
from .forms import ClassForm

TEMPLATE = "schedules/schedules.html"


def _hourly_blocks():
    """5:00, 6:00, 7:00 ... 21:00 (bloques de una hora hasta las 10pm)."""
    t = datetime.combine(date.today(), GymClass.OPEN_TIME)
    end = datetime.combine(date.today(), GymClass.CLOSE_TIME)
    blocks = []
    while t < end:
        blocks.append(t.time())
        t += timedelta(hours=1)
    return blocks


def _format_range(start, end):
    return f"{start:%I:%M %p} - {end:%I:%M %p}".replace("AM", "am").replace("PM", "pm")


def _grid():
    classes = list(GymClass.objects.select_related("service", "instructor", "second_instructor"))
    blocks = _hourly_blocks()
    grid = []
    for i, block in enumerate(blocks):
        next_block = blocks[i + 1] if i + 1 < len(blocks) else GymClass.CLOSE_TIME
        cells = []
        for value, _ in GymClass.Day.choices:
            items = [c for c in classes if c.day == value and block <= c.start_time < next_block]
            cells.append({"day": value, "classes": items, "full": len(items) >= GymClass.MAX_PER_CELL})
        grid.append({"block": block, "block_label": _format_range(block, next_block), "cells": cells})
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

    def form_valid(self, form):
        if form.instance.pk is None:
            form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Clase guardada.")
        return response


class ClassCreate(_Page, CreateView):
    def get_initial(self):
        init = super().get_initial()
        if "day" in self.request.GET:
            init["day"] = self.request.GET["day"]
        if "block" in self.request.GET:
            init["start_time"] = self.request.GET["block"]
        return init


class ClassUpdate(_Page, FullAccessRequiredMixin, UpdateView):
    pass


class ClassDelete(LoginRequiredMixin, FullAccessRequiredMixin, DeleteView):
    model = GymClass
    template_name = TEMPLATE
    success_url = reverse_lazy("schedules:calendar")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_grid())
        ctx["show_delete"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Clase eliminada.")
        return response
