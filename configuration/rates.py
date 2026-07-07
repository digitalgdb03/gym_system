"""Obtención y registro de la tasa BCV en la tabla ExchangeRate (fuente única).

- Fuente primaria: la portada de bcv.org.ve, que expone tanto el USD como su
  "Fecha Valor" (la fecha para la que rige). Si no responde, se usan espejos
  JSON de respaldo (dolarapi.com, pydolarve.org).
- Sábado y domingo: se guardan bajo la fecha del próximo lunes (regla del BCV),
  y solo cuando la fuente confirma, por su fecha de valor, que ya es esa tasa.
"""
import json
import re
import ssl
import time
import urllib.request
from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone

# Portada oficial: única fuente que expone explícitamente la "Fecha Valor"
# (la fecha para la que rige la tasa publicada), por eso es la fuente primaria.
BCV_OFFICIAL_URL = "https://www.bcv.org.ve/"

# Espejos JSON de respaldo si la portada oficial no responde (el sitio del BCV
# tiene historial de caídas). No siempre exponen una fecha confiable.
BCV_ENDPOINTS = [
    "https://ve.dolarapi.com/v1/dolares/oficial",
    "https://pydolarve.org/api/v1/dollar?page=bcv&monitor=usd",
]

_RATE_KEYS = ("promedio", "price", "precio", "rate", "valor")
_DATE_KEYS = ("fechaActualizacion", "fecha_actualizacion", "last_update", "lastUpdate",
              "fecha", "datetime", "date")
_DATE_FORMATS = ("%d/%m/%Y, %I:%M %p", "%d/%m/%Y %I:%M %p", "%d/%m/%Y")
_last_attempt = 0.0   # throttle en memoria para el modo perezoso (dashboard)

_BCV_USD_BLOCK_RE = re.compile(r'id="dolar".*?</div>\s*</div>\s*</div>', re.DOTALL)
_BCV_USD_RATE_RE = re.compile(r'strong-tb">\s*([\d.,]+)\s*<')
_BCV_VALUE_DATE_RE = re.compile(r'Fecha Valor:.*?content="(\d{4}-\d{2}-\d{2})T', re.DOTALL)


def _parse_published_date(value):
    """Extrae una fecha (date) de los formatos que usan estas APIs, o None."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.utc)
        return timezone.localtime(dt).date()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _deep_find_rate_and_date(obj, found_date=None):
    """Recorre el JSON buscando la tasa y, si la fuente la expone, la fecha
    de publicación (para poder confirmar que ya corresponde al día esperado)."""
    if isinstance(obj, dict):
        for k in _DATE_KEYS:
            if found_date is None and k in obj:
                found_date = _parse_published_date(obj[k])
        for k in _RATE_KEYS:
            if k in obj:
                try:
                    v = Decimal(str(obj[k]))
                    if v > 0:
                        return v, found_date
                except Exception:
                    pass
        for v in obj.values():
            r, d = _deep_find_rate_and_date(v, found_date)
            if r is not None:
                return r, d
    elif isinstance(obj, list):
        for v in obj:
            r, d = _deep_find_rate_and_date(v, found_date)
            if r is not None:
                return r, d
    return None, found_date


def _fetch_bcv_official(timeout=6):
    """Consulta la portada de bcv.org.ve y extrae el USD junto con su
    'Fecha Valor' (fecha para la que rige esa tasa). Devuelve (tasa, fecha) o
    (None, None) si la página no responde o cambió de formato."""
    req = urllib.request.Request(
        BCV_OFFICIAL_URL, headers={"User-Agent": "Mozilla/5.0 (ZonaGym/1.0)"})
    # El certificado de bcv.org.ve tiene un defecto conocido (Basic Constraints
    # de la CA no marcado como crítico) que hace fallar la verificación estricta
    # por defecto; se relaja solo para esta petición puntual.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    m_block = _BCV_USD_BLOCK_RE.search(html)
    if not m_block:
        return None, None
    m_rate = _BCV_USD_RATE_RE.search(m_block.group(0))
    if not m_rate:
        return None, None
    try:
        rate = Decimal(m_rate.group(1).replace(".", "").replace(",", "."))
    except Exception:
        return None, None
    if rate <= 0:
        return None, None

    published = None
    m_date = _BCV_VALUE_DATE_RE.search(html[m_block.end():m_block.end() + 1000])
    if m_date:
        try:
            published = date.fromisoformat(m_date.group(1))
        except ValueError:
            pass
    return rate.quantize(Decimal("0.01")), published


def fetch_bcv_rate(timeout=5):
    """Devuelve la tasa oficial (Decimal) o None si no se pudo obtener."""
    rate, _ = fetch_bcv_rate_with_date(timeout)
    return rate


def fetch_bcv_rate_with_date(timeout=5):
    """Devuelve (tasa, fecha_valor). Prioriza la portada oficial del BCV (es la
    única fuente que expone su 'Fecha Valor' de forma confiable); si no
    responde, cae a los espejos JSON de respaldo."""
    try:
        rate, published = _fetch_bcv_official(timeout)
        if rate:
            return rate, published
    except Exception:
        pass

    for url in BCV_ENDPOINTS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ZonaGym/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rate, published = _deep_find_rate_and_date(data)
            if rate and rate > 0:
                return rate.quantize(Decimal("0.01")), published
        except Exception:
            continue
    return None, None


def update_today_rate(force=False):
    """Guarda la tasa del día (bajo su fecha efectiva). Devuelve la fila o None.

    Solo se busca "la próxima tasa" (la del lunes) cuando hoy es sábado o
    domingo. El resto de los días se trabaja siempre con la tasa del día
    actual, sin importar la hora a la que se haga el primer ingreso.

    La fecha de valor que reporta la fuente ("Fecha Valor" de bcv.org.ve, o la
    fecha que reporten los espejos de respaldo) se usa para validar que lo
    obtenido realmente corresponde al día esperado:
    - Fin de semana: si la fuente todavía reporta la tasa del viernes (o no se
      puede confirmar su fecha), no se guarda como la del lunes.
    - Cualquier día: si la fuente ya reporta la tasa del día siguiente (p. ej.
      el BCV la publicó anticipadamente en la tarde/noche), tampoco se guarda
      bajo la fecha de hoy.
    En ambos casos se reintenta más tarde en vez de guardar un valor incorrecto.
    """
    global _last_attempt
    from .models import ExchangeRate

    eff = ExchangeRate.effective_date()          # hoy, o el lunes si es finde
    is_weekend = eff != timezone.localdate()
    existing = ExchangeRate.objects.filter(date=eff).first()
    if existing and not force:
        return existing
    if not force and (time.time() - _last_attempt) < 1800:   # no reintentar antes de 30 min
        return None
    _last_attempt = time.time()

    rate, published = fetch_bcv_rate_with_date()
    if rate is None:
        return None

    if published is not None:
        if published > eff:
            return existing   # la fuente ya muestra la tasa del día siguiente: no es la de hoy
        if is_weekend and published < eff:
            return existing   # todavía es la tasa del viernes, no la del lunes
    elif is_weekend:
        return existing       # sin fecha confirmada, no se puede saber si ya es la del lunes

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