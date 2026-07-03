from decimal import Decimal, InvalidOperation
from django import template
from configuration.models import GymConfig

register = template.Library()


@register.filter
def bs(value):
    """Convierte un monto USD a bolívares con la tasa BCV vigente (formato es-VE)."""
    try:
        usd = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return value
    rate = GymConfig.load().bcv_rate      # property -> ExchangeRate.current()
    if not rate:
        return "—"                        # aún no hay tasa registrada
    total = usd * rate
    s = f"{total:,.2f}"                                    # 1,234.50 (US)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234,50


@register.filter
def initials(name):
    return "".join(w[0] for w in (name or "").split()[:2]).upper()