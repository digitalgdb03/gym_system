from datetime import datetime
from datetime import time as dt_time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from client.models import Client
from configuration.utils import is_ajax, paginate
from .models import Attendance, normalize_id


@login_required
def attendance_list(request):
    today = timezone.localdate()
    records = Attendance.objects.filter(check_in__date=today).select_related("client")
    q = request.GET.get("q", "").strip()
    if q:
        q_id = normalize_id(q)
        records = records.filter(
            Q(client__full_name__icontains=q) | Q(client__id_card__icontains=q_id)
        )
    page = paginate(request, records)
    if is_ajax(request):
        return render(request, "attendance/_results.html", {"records": page, "page_obj": page})
    context = {
        "records": page,
        "page_obj": page,
        "inside": records.filter(check_out__isnull=True).count(),
        "total": records.count(),
        "distinct": records.values("client").distinct().count(),
        "doc_types": ["V", "E", "J", "P"],
        "just_marked": request.session.pop("just_marked", None),
    }
    return render(request, "attendance/list.html", context)


@login_required
def mark_entry(request):
    if request.method == "POST":
        doc = request.POST.get("doc_type", "V")
        number = request.POST.get("number", "").strip()
        if not normalize_id(number):
            messages.error(request, "Ingresa el número de cédula.")
            return redirect("attendance:list")

        target = normalize_id(number)
        client = next(
            (c for c in Client.objects.filter(doc_type=doc) if normalize_id(c.id_card) == target),
            None,
        )
        if not client:
            messages.error(request, f"No se encontró un cliente con la cédula {doc}-{number}.")
            return redirect("attendance:list")

        today = timezone.localdate()
        open_entries = Attendance.objects.filter(client=client, check_out__isnull=True)

        if open_entries.filter(check_in__date=today).exists():
            request.session["just_marked"] = {
                "name": client.full_name, "id_card": client.full_id,
                "status": "ERROR", "status_display": "En el gimnasio",
                "message": "Esta persona ya marcó entrada hoy y no ha registrado su salida. "
                           "Registra primero su salida para volver a marcar.",
            }
            return redirect("attendance:list")

        # Entradas abiertas de días ANTERIORES (olvidaron marcar salida):
        # se cierran automáticamente al final de su propio día.
        for rec in open_entries.filter(check_in__date__lt=today):
            local_day = timezone.localtime(rec.check_in).date()
            rec.check_out = timezone.make_aware(datetime.combine(local_day, dt_time(23, 59)))
            rec.save(update_fields=["check_out"])

        # Registra la entrada de hoy y dispara la tarjeta con estatus + plan + instructor.
        Attendance.objects.create(client=client, created_by=request.user)
        request.session["just_marked"] = {
            "name": client.full_name, "id_card": client.full_id,
            "status": client.status, "status_display": client.get_status_display(),
            "plan": client.plans_summary or "Sin plan",
            "trainer": client.trainers_summary or "—",
        }
    return redirect("attendance:list")


@login_required
def check_out(request, pk):
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == "POST" and record.check_out is None:
        record.check_out = timezone.now()
        record.save(update_fields=["check_out"])
        messages.success(request, "Salida registrada.")
    return redirect("attendance:list")
