from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from client.models import Client
from .models import Attendance, normalize_id


@login_required
def attendance_list(request):
    today = timezone.localdate()
    records = Attendance.objects.filter(check_in__date=today).select_related("client")
    context = {
        "records": records,
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

        target = normalize_id(doc + number)
        client = next((c for c in Client.objects.all() if normalize_id(c.id_card) == target), None)
        if not client:
            messages.error(request, f"No se encontró un cliente con la cédula {doc}-{number}.")
            return redirect("attendance:list")

        Attendance.objects.create(client=client)
        request.session["just_marked"] = {
            "name": client.full_name, "id_card": client.id_card,
            "status": client.status, "status_display": client.get_status_display(),
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


@login_required
def delete_record(request, pk):
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == "POST":
        record.delete()
        messages.success(request, "Registro eliminado.")
    return redirect("attendance:list")
