from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from configuration.models import GymConfig

NAVY = colors.HexColor("#343959")
GRID = colors.HexColor("#dddddd")
ZEBRA = colors.HexColor("#f5f5f7")
MUTED = colors.HexColor("#777777")
LOGO_PATH = settings.BASE_DIR / "static" / "images" / "zona_gym.png"

FONT_NAME = "Helvetica"
FONT_SIZE = 8
MIN_COL_WIDTH = 1.6 * cm
PLAN_CELL_WIDTH = 7.5 * cm  # ancho fijo para celdas de varias líneas (Paragraph)

PLAN_CELL_STYLE = ParagraphStyle("PlanCell", fontName=FONT_NAME, fontSize=7.5,
                                 leading=10, textColor=colors.black)


def build_plan_cell(memberships):
    """Celda con el detalle de cada plan del cliente: nombre, fechas, días
    restantes/de mora y entrenador (si tiene), una línea por plan."""
    if not memberships:
        return "Sin plan"
    lines = []
    for m in memberships:
        start = m.start_date.strftime("%d/%m/%y") if m.start_date else "—"
        end = m.end_date.strftime("%d/%m/%y") if m.end_date else "—"
        line = f"<b>{escape(m.plan.label)}</b>: {start}-{end}"
        badge = m.days_badge
        if badge:
            line += f" ({escape(badge[0])})"
        if m.trainer:
            line += f" · Entr: {escape(m.trainer.full_name)}"
        lines.append(line)
    return Paragraph("<br/>".join(lines), PLAN_CELL_STYLE)


def _cell_width(cell):
    if isinstance(cell, Paragraph):
        return PLAN_CELL_WIDTH
    return stringWidth(str(cell), FONT_NAME, FONT_SIZE) + 18


def _col_widths(columns, rows, available_width):
    """Ancho de cada columna proporcional a su contenido más largo, escalado
    para que la tabla ocupe exactamente el ancho disponible de la página."""
    widths = []
    for i in range(len(columns)):
        cells = [columns[i]] + [r[i] for r in rows]
        natural = max((_cell_width(c) for c in cells), default=0)
        widths.append(max(natural, MIN_COL_WIDTH))
    total = sum(widths) or 1
    scale = available_width / total
    return [w * scale for w in widths]


def _table_flowable(columns, rows, available_width):
    data = [columns] + rows
    table = Table(data, colWidths=_col_widths(columns, rows, available_width), repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def build_report_pdf(title, sections, filename, subtitle=""):
    """PDF con cabecera (logo + nombre del sistema + título del reporte +
    fecha de generación) y los registros en una o varias tablas, cada una
    ajustada al ancho de la página.

    'sections' es una lista de dicts: {"heading": str opcional, "columns": [...], "rows": [[...], ...]}.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.3 * cm, bottomMargin=1.3 * cm,
        title=title,
    )
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle("GymName", parent=styles["Title"], fontSize=18,
                                textColor=NAVY, spaceAfter=0, leading=20)
    title_style = ParagraphStyle("ReportTitle", parent=styles["Normal"], fontSize=13,
                                 textColor=colors.black, spaceBefore=2, spaceAfter=0)
    sub_style = ParagraphStyle("ReportSub", parent=styles["Normal"], fontSize=9,
                               textColor=MUTED, spaceBefore=2)
    date_style = ParagraphStyle("GenDate", parent=styles["Normal"], fontSize=9,
                                textColor=MUTED, alignment=TA_RIGHT)
    heading_style = ParagraphStyle("SectionHeading", parent=styles["Heading3"], fontSize=11,
                                   textColor=NAVY, spaceBefore=14, spaceAfter=6)

    gym_name = GymConfig.load().name or "Zona Gym"
    generated = timezone.localtime().strftime("%d/%m/%Y %I:%M %p")

    name_cell = [Paragraph(gym_name, name_style), Paragraph(title, title_style)]
    if LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=1.6 * cm, height=1.6 * cm)
        header = Table([[logo, name_cell, Paragraph(f"Generado: {generated}", date_style)]],
                        colWidths=[2 * cm, None, 6 * cm])
    else:
        header = Table([[name_cell, Paragraph(f"Generado: {generated}", date_style)]],
                        colWidths=[None, 6 * cm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    elements = [header]
    if subtitle:
        elements.append(Paragraph(subtitle, sub_style))
    elements.append(Spacer(1, 12))

    available_width = doc.width
    for i, section in enumerate(sections):
        if i > 0:
            elements.append(Spacer(1, 4))
        heading = section.get("heading")
        if heading:
            elements.append(Paragraph(heading, heading_style))
        rows = section["rows"]
        if rows:
            elements.append(_table_flowable(section["columns"], rows, available_width))
        else:
            elements.append(Paragraph("Sin registros para los filtros seleccionados.", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
