"""Obtención y registro de la tasa BCV en la tabla ExchangeRate (fuente única).

- Días hábiles: se guarda bajo el día (el viernes conserva su propia tasa) y solo
  se auto-actualiza antes de la hora de publicación del BCV.
- Sábado y domingo: se guardan bajo la fecha del próximo lunes (regla del BCV).
"""
import json
import time
import urllib.request
from decimal import Decimal

BCV_ENDPOINTS = [
    "https://ve.dolarapi.com/v1/dolares/oficial",
    "https://pydolarve.org/api/v1/dollar?page=bcv&monitor=usd",
]

_RATE_KEYS = ("promedio", "price", "precio", "rate", "valor")
_last_attempt = 0.0   # throttle en memoria para el modo perezoso (dashboard)


def _deep_find_rate(obj):
    if isinstance(obj, dict):
        for k in _RATE_KEYS:
            if k in obj:
                try:
                    v = Decimal(str(obj[k]))
                    if v > 0:
                        return v
                except Exception:
                    pass
        for v in obj.values():
            r = _deep_find_rate(v)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _deep_find_rate(v)
            if r is not None:
                return r
    return None


def fetch_bcv_rate(timeout=5):
    """Devuelve la tasa oficial (Decimal) o None si no se pudo obtener."""
    for url in BCV_ENDPOINTS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ZonaGym/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rate = _deep_find_rate(data)
            if rate and rate > 0:
                return rate.quantize(Decimal("0.01"))
        except Exception:
            continue
    return None


def update_today_rate(force=False):
    """Guarda la tasa del día (bajo su fecha efectiva). Devuelve la fila o None.

    En días hábiles no actualiza automáticamente después de la hora de publicación
    del BCV, para que el viernes conserve su tasa y no capture la del lunes.
    """
    global _last_attempt
    from .models import ExchangeRate

    # Protección: en día hábil por la tarde no auto-actualizamos (salvo force manual).
    if not force and not ExchangeRate.can_auto_update():
        return ExchangeRate.for_today()

    eff = ExchangeRate.effective_date()          # hoy, o el lunes si es finde
    existing = ExchangeRate.objects.filter(date=eff).first()
    if existing and not force:
        return existing
    if not force and (time.time() - _last_attempt) < 1800:   # no reintentar antes de 30 min
        return None
    _last_attempt = time.time()

    rate = fetch_bcv_rate()
    if rate is None:
        return None

    obj, _ = ExchangeRate.objects.update_or_create(
        date=eff, defaults={"rate": rate, "source": ExchangeRate.Source.AUTO}
    )
    return obj


def set_manual_rate(rate):
    """Registra la tasa a mano bajo su fecha efectiva (sáb/dom -> lunes; viernes -> viernes)."""
    from .models import ExchangeRate
    eff = ExchangeRate.effective_date()
    return ExchangeRate.objects.update_or_create(
        date=eff, defaults={"rate": Decimal(str(rate)), "source": ExchangeRate.Source.MANUAL},
    )[0]