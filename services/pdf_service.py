import io
import os
from datetime import datetime

import pytz
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import LOGO_PATH, TIMEZONE

_tz = pytz.timezone(TIMEZONE)
_styles = getSampleStyleSheet()

_HEADER_COLOR = colors.HexColor("#1A237E")
_ROW_ALT_COLOR = colors.HexColor("#F4F6FF")
_TITLE_STYLE = ParagraphStyle(
    "TituloReporte",
    parent=_styles["Title"],
    fontSize=15,
    textColor=_HEADER_COLOR,
    spaceAfter=4,
)

_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), _HEADER_COLOR),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT_COLOR]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
])

def _fecha_reporte():
    return datetime.now(_tz).strftime("%d/%m/%Y %H:%M")

def _safe_str(valor):
    s = str(valor)
    return "" if s.lower() == "nan" else s

def _agregar_logo(elementos):
    if os.path.exists(LOGO_PATH):
        try:
            img = Image(LOGO_PATH, width=80, height=40)
            img.hAlign = "LEFT"
            elementos.append(img)
        except Exception:
            pass

def generar_pdf_pedido(lista):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    elementos = []
    _agregar_logo(elementos)
    elementos.append(Paragraph("PROGRAMACIÓN PEDIDO YODO I131", _TITLE_STYLE))
    elementos.append(Paragraph(f"Fecha Reporte: {_fecha_reporte()}", _styles["Normal"]))
    elementos.append(Spacer(1, 15))

    data = [["PACIENTE", "IDENTIFICACIÓN", "ENTIDAD", "FECHA TOMA", "mCi"]]
    for p in lista:
        if p.get("Estado") not in ("CANCELADO", "DECAIMIENTO"):
            data.append([
                p.get("Nombre", ""),
                p.get("ID", ""),
                p.get("Entidad", ""),
                _safe_str(p.get("Fecha_Capsula", "")),
                str(p.get("mCI", "")),
            ])

    tabla = Table(data, colWidths=[180, 100, 120, 80, 50])
    tabla.setStyle(_TABLE_STYLE)
    elementos.append(tabla)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

def generar_pdf_trazabilidad(lista):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    elementos = []
    _agregar_logo(elementos)
    elementos.append(Paragraph("REPORTE DE TRAZABILIDAD Y MOVIMIENTO", _TITLE_STYLE))
    elementos.append(Paragraph(f"Fecha Reporte: {_fecha_reporte()}", _styles["Normal"]))
    elementos.append(Spacer(1, 15))

    data = [["PACIENTE / ID", "ENTIDAD", "mCI", "ESTADO", "F. RECEPCIÓN", "F. ADMIN.", "OBSERVACIONES"]]
    for p in lista:
        data.append([
            Paragraph(f"<b>{p.get('Nombre','')}</b><br/>{p.get('ID','')}", _styles["Normal"]),
            p.get("Entidad", ""),
            str(p.get("mCI", "")),
            p.get("Estado", ""),
            _safe_str(p.get("Fecha_Recepcion", "")),
            _safe_str(p.get("Fecha_Administracion", "")),
            Paragraph(_safe_str(p.get("Notas", "")), _styles["Normal"]),
        ])

    tabla = Table(data, colWidths=[140, 90, 40, 80, 85, 85, 200])
    tabla.setStyle(_TABLE_STYLE)
    elementos.append(tabla)
    doc.build(elementos)
    buffer.seek(0)
    return buffer
