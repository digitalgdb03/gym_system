from collections import Counter
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from configuration.choices import DocType
from configuration.models import ExchangeRate
from configuration.rates import update_today_rate
from configuration.utils import paginate
from configuration.templatetags.gym_extras import bs
from attendance.models import Attendance
from client.models import Client
from configuration.models import GymConfig
from payments.models import Payment
from plans.models import Plan
from schedules.models import GymClass
from services.models import Service
from user.models import User
from user.permissions import full_access_required
from .pdf import build_report_pdf

DAY_SHORT = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]      # weekday(): lunes = 0
METHOD_ABBR = {"CASH_USD": "Efec. $", "CASH_BS": "Efec. Bs", "MOBILE": "P. Móvil",
               "TRANSFER": "Transf.", "CARD": "Punto"}
TABS = ("resumen", "clientes", "planes", "pagos")


def _hour_label(h):
    if h == 12:
        return "12m"
    return f"{h if h <= 12 else h - 12}{'a' if h < 12 else 'p'}"


def _with_pct(serie):
    top = max((s["val"] for s in serie), default=1) or 1
    for s in serie:
        s["pct"] = round(float(s["val"]) / float(top) * 100)   # entero → sin coma decimal
    return serie


@login_required
def dashboard(request):
    today = timezone.localdate()
    if not ExchangeRate.for_today():
        update_today_rate()
    cfg = GymConfig.load()

    todays_payments = Payment.objects.filter(created_at__date=today).select_related("client", "plan")
    income = todays_payments.aggregate(s=Sum("amount_usd"))["s"] or 0

    for c in Client.objects.prefetch_related("memberships").exclude(status=Client.Status.FROZEN):
        c.recompute_status()

    active  = Client.objects.filter(status=Client.Status.ACTIVE).count()
    overdue = Client.objects.filter(status=Client.Status.OVERDUE).count()
    frozen  = Client.objects.filter(status=Client.Status.FROZEN).count()
    total_cli = active + overdue + frozen or 1

    todays_att = Attendance.objects.filter(check_in__date=today)
    counts = Counter(a.check_in.hour for a in todays_att)
    hourly = _with_pct([{"label": _hour_label(h), "val": counts[h]} for h in sorted(counts)])

    top_block_row = (GymClass.objects.values("start_time", "end_time").annotate(n=Count("id"))
                     .order_by("-n").first())
    if top_block_row:
        st, et = top_block_row["start_time"], top_block_row["end_time"]
        top_block = f"{st:%I:%M %p} - {et:%I:%M %p}".replace("AM", "am").replace("PM", "pm")
    else:
        top_block = "—"
    top_service = (GymClass.objects.values("service__name").annotate(n=Count("id"))
                   .order_by("-n").first() or {}).get("service__name", "—")

    context = {
        "cfg": cfg, "income": income,
        "inside": todays_att.filter(check_out__isnull=True).count(),
        "active": active, "overdue": overdue, "frozen": frozen,
        "pct_active": round(active / total_cli * 100),
        "pct_active_overdue": round((active + overdue) / total_cli * 100),
        "hourly": hourly, "top_block": top_block, "top_service": top_service,
        "latest_payments": todays_payments[:4],
    }
    return render(request, "report/dashboard.html", context)


def _summary_data(request):
    today = timezone.localdate()
    period = request.GET.get("period", "week")
    span = {"day": 1, "week": 7, "month": 30}.get(period, 7)
    start = today - timedelta(days=span - 1)

    qs = Payment.objects.filter(created_at__date__gte=start).select_related("plan__service")
    total = qs.aggregate(s=Sum("amount_usd"))["s"] or 0
    count = qs.count()
    avg = total / count if count else 0

    if period == "day":
        serie = [{"label": METHOD_ABBR.get(v, v),
                  "val": qs.filter(method=v).aggregate(s=Sum("amount_usd"))["s"] or 0}
                 for v, _ in Payment.Method.choices]
        chart_title = "Ingresos por método (hoy)"
    elif period == "month":
        buckets = [0] * 5
        for p in qs:
            idx = 4 - min(4, (today - p.created_at.astimezone().date()).days // 7)
            buckets[idx] += p.amount_usd
        serie = [{"label": "Esta sem." if i == 4 else f"Sem -{4 - i}", "val": buckets[i]} for i in range(5)]
        chart_title = "Ingresos por semana (últimos 30 días)"
    else:
        serie = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            serie.append({"label": DAY_SHORT[d.weekday()],
                          "val": qs.filter(created_at__date=d).aggregate(s=Sum("amount_usd"))["s"] or 0})
        chart_title = "Ingresos por día (últimos 7 días)"

    by_method = [{"label": label, "count": qs.filter(method=v).count(),
                  "total": qs.filter(method=v).aggregate(s=Sum("amount_usd"))["s"] or 0}
                 for v, label in Payment.Method.choices if qs.filter(method=v).exists()]

    by_area = [{"label": r["plan__service__name"], "count": r["n"], "total": r["t"]}
               for r in qs.values("plan__service__name").annotate(n=Count("id"), t=Sum("amount_usd"))]

    staff_stats = []
    for u in User.objects.all():
        payments_qs = Payment.objects.filter(created_by=u, created_at__date__gte=start)
        stats = {
            "name": u.full_name or u.username,
            "role": u.roles_label,
            "clients": Client.objects.filter(created_by=u, created_at__date__gte=start).count(),
            "payments": payments_qs.count(),
            "amount": payments_qs.aggregate(s=Sum("amount_usd"))["s"] or 0,
            "attendances": Attendance.objects.filter(created_by=u, check_in__date__gte=start).count(),
        }
        stats["total_actions"] = stats["clients"] + stats["payments"] + stats["attendances"]
        staff_stats.append(stats)
    staff_stats.sort(key=lambda s: s["total_actions"], reverse=True)

    return {
        "period": period, "chart_title": chart_title, "serie": _with_pct(serie),
        "total": total, "count": count, "avg": avg,
        "by_method": by_method, "by_area": by_area,
        "staff_stats": staff_stats,
    }


def _summary_context(request):
    data = _summary_data(request)
    staff_page = paginate(request, data["staff_stats"])
    data["staff_stats"] = staff_page
    data["page_obj"] = staff_page
    return data


def _clients_queryset(request):
    qs = Client.objects.prefetch_related("memberships__plan__service").order_by("full_name")
    q = request.GET.get("cli_q", "").strip()
    status = request.GET.get("cli_status", "")
    doc_type = request.GET.get("cli_doc_type", "")
    if q:
        q_id = q.replace(".", "").replace("-", "")
        qs = qs.filter(Q(full_name__icontains=q) | Q(id_card__icontains=q_id))
    if status in dict(Client.Status.choices):
        qs = qs.filter(status=status)
    if doc_type in dict(DocType.choices):
        qs = qs.filter(doc_type=doc_type)
    return qs


def _clients_context(request):
    qs = _clients_queryset(request)
    page = paginate(request, qs, per_page=15)
    for c in page:
        c.recompute_status()
    return {
        "clients": page,
        "page_obj": page,
        "clients_status_choices": Client.Status.choices,
        "clients_doc_choices": DocType.choices,
        "cli_q": request.GET.get("cli_q", ""),
        "cli_status": request.GET.get("cli_status", ""),
        "cli_doc_type": request.GET.get("cli_doc_type", ""),
    }


def _clients_rows(qs):
    rows = []
    for c in qs:
        c.recompute_status()
        rows.append([c.full_name, c.full_id, c.get_status_display(), c.phone or "—",
                     c.plans_summary or "Sin plan", c.created_at.strftime("%d/%m/%Y")])
    return rows


def _plans_queryset(request):
    qs = Plan.objects.select_related("service").order_by("service__name", "duration")
    service = request.GET.get("pl_service", "")
    duration = request.GET.get("pl_duration", "")
    is_custom = request.GET.get("pl_custom", "")
    if service:
        qs = qs.filter(service_id=service)
    if duration in dict(Plan.Duration.choices):
        qs = qs.filter(duration=duration)
    if is_custom == "1":
        qs = qs.filter(is_custom=True)
    elif is_custom == "0":
        qs = qs.filter(is_custom=False)
    return qs


def _plans_context(request):
    qs = _plans_queryset(request)
    page = paginate(request, qs, per_page=15)
    return {
        "report_plans": page,
        "page_obj": page,
        "plans_services": Service.objects.order_by("name"),
        "plans_duration_choices": Plan.Duration.choices,
        "pl_service": request.GET.get("pl_service", ""),
        "pl_duration": request.GET.get("pl_duration", ""),
        "pl_custom": request.GET.get("pl_custom", ""),
    }


def _plans_rows(qs):
    return [[p.service.name, p.label, p.get_duration_display(),
              f"${p.price_bcv}", f"${p.price_cash}",
              "Sí" if p.is_custom else "No", "Sí" if p.is_active else "No"] for p in qs]


def _payments_queryset(request):
    qs = Payment.objects.select_related("client", "plan", "plan__service").order_by("-created_at")
    q = request.GET.get("pay_q", "").strip()
    method = request.GET.get("pay_method", "")
    date_from = request.GET.get("pay_from", "")
    date_to = request.GET.get("pay_to", "")
    is_custom = request.GET.get("pay_custom", "")
    if q:
        q_id = q.replace(".", "").replace("-", "")
        qs = qs.filter(Q(client__full_name__icontains=q) | Q(client__id_card__icontains=q_id))
    if method in dict(Payment.Method.choices):
        qs = qs.filter(method=method)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if is_custom == "1":
        qs = qs.filter(is_custom=True)
    elif is_custom == "0":
        qs = qs.filter(is_custom=False)
    return qs


def _payments_context(request):
    qs = _payments_queryset(request)
    page = paginate(request, qs, per_page=15)
    return {
        "report_payments": page,
        "page_obj": page,
        "payments_method_choices": Payment.Method.choices,
        "pay_q": request.GET.get("pay_q", ""),
        "pay_method": request.GET.get("pay_method", ""),
        "pay_from": request.GET.get("pay_from", ""),
        "pay_to": request.GET.get("pay_to", ""),
        "pay_custom": request.GET.get("pay_custom", ""),
    }


def _payments_rows(qs):
    return [[p.client.full_name, p.plan.label, p.get_method_display(),
              f"${p.amount_usd}", f"Bs {p.amount_bs}" if p.amount_bs else "—",
              "Sí" if p.is_custom else "No", p.created_at.strftime("%d/%m/%Y %I:%M %p")] for p in qs]


@login_required
@full_access_required
def reports(request):
    tab = request.GET.get("tab", "resumen")
    if tab not in TABS:
        tab = "resumen"

    context = {"tab": tab}
    if tab == "clientes":
        context.update(_clients_context(request))
    elif tab == "planes":
        context.update(_plans_context(request))
    elif tab == "pagos":
        context.update(_payments_context(request))
    else:
        context.update(_summary_context(request))

    params = request.GET.copy()
    params["tab"] = tab
    context["pdf_url"] = f"{reverse('report:reports_pdf')}?{params.urlencode()}"
    return render(request, "report/reports.html", context)


@login_required
@full_access_required
def reports_pdf(request):
    tab = request.GET.get("tab", "resumen")
    if tab not in TABS:
        tab = "resumen"
    stamp = timezone.localdate().strftime("%Y%m%d")

    if tab == "clientes":
        rows = _clients_rows(_clients_queryset(request))
        sections = [{"columns": ["Cliente", "Documento", "Estado", "Teléfono", "Plan(es)", "Registrado"],
                     "rows": rows}]
        return build_report_pdf("Reporte de clientes", sections, f"reporte_clientes_{stamp}.pdf")

    if tab == "planes":
        rows = _plans_rows(_plans_queryset(request))
        sections = [{"columns": ["Área", "Plan", "Duración", "Precio BCV", "Precio efectivo", "Personalizado", "Activo"],
                     "rows": rows}]
        return build_report_pdf("Reporte de planes", sections, f"reporte_planes_{stamp}.pdf")

    if tab == "pagos":
        rows = _payments_rows(_payments_queryset(request))
        sections = [{"columns": ["Cliente", "Plan", "Método", "Monto USD", "Monto Bs", "Personalizado", "Fecha"],
                     "rows": rows}]
        return build_report_pdf("Reporte de pagos", sections, f"reporte_pagos_{stamp}.pdf")

    data = _summary_data(request)
    sections = [
        {
            "heading": data["chart_title"],
            "columns": ["Total recaudado (USD)", "Total recaudado (Bs)", "Pagos", "Ticket promedio (USD)"],
            "rows": [[f"${data['total']}", f"Bs {bs(data['total'])}", data["count"], f"${round(data['avg'], 2)}"]],
        },
        {
            "heading": "Por método de pago",
            "columns": ["Concepto", "Pagos", "Total (USD)", "Total (Bs)"],
            "rows": [[r["label"], r["count"], f"${r['total']}", f"Bs {bs(r['total'])}"] for r in data["by_method"]],
        },
        {
            "heading": "Por área",
            "columns": ["Concepto", "Pagos", "Total (USD)", "Total (Bs)"],
            "rows": [[r["label"], r["count"], f"${r['total']}", f"Bs {bs(r['total'])}"] for r in data["by_area"]],
        },
        {
            "heading": "Estadísticas por usuario",
            "columns": ["Usuario", "Rol", "Clientes registrados", "Pagos procesados", "Monto procesado (USD)", "Asistencias marcadas"],
            "rows": [[s["name"], s["role"], s["clients"], s["payments"], f"${s['amount']}", s["attendances"]]
                     for s in data["staff_stats"]],
        },
    ]
    return build_report_pdf("Resumen de ingresos", sections, f"reporte_resumen_{stamp}.pdf")
