from datetime import datetime
from datetime import time as dt_time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from client.forms import ClientForm, InitialPaymentForm
from client.models import Client
from client.views import register_client_with_payment
from configuration.utils import is_ajax, paginate, plan_prices_json, plan_trainer_map_json, client_plan_end_dates_json
from .models import Attendance, normalize_id


def _list_context(request):
    today = timezone.localdate()
    records = Attendance.objects.filter(check_in__date=today).select_related("client").prefetch_related(
        "client__memberships__plan__service", "client__memberships__trainer"
    )
    q = request.GET.get("q", "").strip()
    if q:
        q_id = normalize_id(q)
        records = records.filter(
            Q(client__full_name__icontains=q) | Q(client__id_card__icontains=q_id)
        )
    page = paginate(request, records)
    return {
        "records": page,
        "page_obj": page,
        "inside": records.filter(check_out__isnull=True).count(),
        "total": records.count(),
        "distinct": records.values("client").distinct().count(),
        "doc_types": ["V", "E", "J", "P"],
    }


def _mark_attendance(client, user):
    """Registra la entrada de hoy y arma la tarjeta de estatus + todos los
    planes del cliente (inicio, fin, días y entrenador de cada uno)."""
    Attendance.objects.create(client=client, created_by=user)
    plans = []
    for m in client.memberships.select_related("plan", "trainer").all():
        badge = m.days_badge
        plans.append({
            "label": m.plan.label,
            "start": m.start_date.strftime("%d/%m/%Y") if m.start_date else "",
            "end": m.end_date.strftime("%d/%m/%Y") if m.end_date else "",
            "days_label": badge[0] if badge else "",
            "days_class": badge[1] if badge else "",
            "trainer": m.trainer.full_name if m.trainer else "",
        })
    return {
        "name": client.full_name, "id_card": client.full_id,
        "status": client.status, "status_display": client.get_status_display(),
        "plans": plans,
    }


@login_required
def attendance_list(request):
    ctx = _list_context(request)
    if is_ajax(request):
        return render(request, "attendance/_results.html", ctx)
    ctx["just_marked"] = request.session.pop("just_marked", None)
    ctx["client_not_found"] = request.session.pop("client_not_found", None)
    return render(request, "attendance/list.html", ctx)


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
            # No existe: se le pregunta al usuario si quiere registrarlo,
            # en vez de solo mostrar un error.
            request.session["client_not_found"] = {"doc_type": doc, "number": number}
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
        request.session["just_marked"] = _mark_attendance(client, request.user)
    return redirect("attendance:list")


@login_required
def register_client(request):
    """Si al marcar asistencia la cédula no corresponde a ningún cliente y
    el usuario acepta registrarlo, se da de alta con su pago inicial (mismo
    flujo que en Clientes/Pagos) y se marca su entrada de una vez."""
    doc_type = request.GET.get("doc_type") or request.POST.get("doc_type") or "V"
    number = request.GET.get("number") or request.POST.get("number") or ""

    if request.method == "POST":
        form = ClientForm(request.POST)
        payment_form = InitialPaymentForm(request.POST)
        if form.is_valid() and payment_form.is_valid():
            client, _m = register_client_with_payment(form, payment_form, request.user)
            request.session["just_marked"] = _mark_attendance(client, request.user)
            messages.success(request, "Cliente registrado y entrada marcada.")
            return redirect("attendance:list")
    else:
        form = ClientForm(initial={"doc_type": doc_type, "id_card": number})
        payment_form = InitialPaymentForm()

    ctx = _list_context(request)
    ctx.update({
        "show_register": True,
        "register_form": form,
        "register_payment_form": payment_form,
        "plan_trainer_map_json": plan_trainer_map_json(),
        "plan_prices_json": plan_prices_json(),
        "client_plan_end_dates_json": client_plan_end_dates_json(),
    })
    return render(request, "attendance/list.html", ctx)


@login_required
def check_out(request, pk):
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == "POST" and record.check_out is None:
        record.check_out = timezone.now()
        record.save(update_fields=["check_out"])
        messages.success(request, "Salida registrada.")
    return redirect("attendance:list")
