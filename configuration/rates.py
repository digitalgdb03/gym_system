"""Obtención y registro de la tasa BCV.

- fetch_bcv_rate(): consulta APIs públicas del dólar oficial (BCV) y devuelve Decimal o None.
- update_today_rate(): guarda/actualiza la tasa de HOY en ExchangeRate y la refleja en GymConfig.
  Es best-effort: si no hay conexión, no rompe nada (conserva la tasa manual/anterior).
"""
import json
import time
import urllib.request
from decimal import Decimal

# APIs públicas del dólar oficial de Venezuela (BCV). Se prueban en orden.
BCV_ENDPOINTS = [
    "https://ve.dolarapi.com/v1/dolares/oficial",
    "https://pydolarve.org/api/v1/dollar?page=bcv&monitor=usd",
]

_RATE_KEYS = ("promedio", "price", "precio", "rate", "valor")
_last_attempt = 0.0   # throttle en memoria para el modo perezoso (dashboard)


def _deep_find_rate(obj):
    """Busca el primer número plausible bajo claves típicas de precio."""
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
    """Guarda la tasa de hoy desde la API. Devuelve la fila o None si no se obtuvo.

    force=False (modo perezoso): si ya hay tasa de hoy no hace nada; si no, reintenta
    a lo sumo cada 30 min para no colgar la carga de páginas cuando el BCV está caído.
    """
    global _last_attempt
    from django.utils import timezone
    from .models import GymConfig, ExchangeRate

    today = timezone.localdate()
    existing = ExchangeRate.objects.filter(date=today).first()
    if existing and not force:
        return existing
    if not force and (time.time() - _last_attempt) < 1800:
        return None
    _last_attempt = time.time()

    rate = fetch_bcv_rate()
    if rate is None:
        return None

    obj, _ = ExchangeRate.objects.update_or_create(
        date=today, defaults={"rate": rate, "source": ExchangeRate.Source.AUTO}
    )
    cfg = GymConfig.load()
    if cfg.bcv_rate != rate:
        cfg.bcv_rate = rate
        cfg.save(update_fields=["bcv_rate"])
    return obj


def set_manual_rate(rate):
    """Registra la tasa de hoy como MANUAL (cuando se edita a mano en Configuración)."""
    from django.utils import timezone
    from .models import ExchangeRate
    today = timezone.localdate()
    obj, _ = ExchangeRate.objects.update_or_create(
        date=today, defaults={"rate": Decimal(str(rate)), "source": ExchangeRate.Source.MANUAL}
    )
    return obj