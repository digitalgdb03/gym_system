from collections import Counter
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone
from configuration.models import ExchangeRate
from configuration.rates import update_today_rate
from attendance.models import Attendance
from client.models import Client
from configuration.models import GymConfig
from payments.models import Payment
from schedules.models import GymClass
from user.models import User

DAY_SHORT = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]      # weekday(): lunes = 0
METHOD_ABBR = {"CASH_USD": "Efec. $", "CASH_BS": "Efec. Bs", "MOBILE": "P. Móvil",
               "TRANSFER": "Transf.", "CARD": "Punto"}


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


@login_required
def reports(request):
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
            "role": u.get_role_display(),
            "clients": Client.objects.filter(created_by=u, created_at__date__gte=start).count(),
            "payments": payments_qs.count(),
            "amount": payments_qs.aggregate(s=Sum("amount_usd"))["s"] or 0,
            "attendances": Attendance.objects.filter(created_by=u, check_in__date__gte=start).count(),
        }
        stats["total_actions"] = stats["clients"] + stats["payments"] + stats["attendances"]
        staff_stats.append(stats)
    staff_stats.sort(key=lambda s: s["total_actions"], reverse=True)

    context = {
        "period": period, "chart_title": chart_title, "serie": _with_pct(serie),
        "total": total, "count": count, "avg": avg,
        "by_method": by_method, "by_area": by_area,
        "staff_stats": staff_stats,
    }
    return render(request, "report/reports.html", context)
