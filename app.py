import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
import os
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"
LOGO_PATH = "logo.png" 

st.set_page_config(page_title="Nuclear 2000 Ltda", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            return df.to_dict('records')
    except: pass
    return []

def generar_pdf(lista, tipo="PEDIDO"):
    buffer = io.BytesIO()
    orientacion = letter if tipo == "PEDIDO" else landscape(letter)
    doc = SimpleDocTemplate(buffer, pagesize=orientacion, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    elementos = []
    styles = getSampleStyleSheet()
    
    if os.path.exists(LOGO_PATH):
        try:
            img = Image(LOGO_PATH, width=80, height=40); img.hAlign = 'LEFT'
            elementos.append(img)
        except: pass
    
    titulo = "PROGRAMACIÓN PEDIDO YODO I131" if tipo == "PEDIDO" else "REPORTE DE TRAZABILIDAD Y MOVIMIENTO"
    elementos.append(Paragraph(f"<b>{titulo}</b>", ParagraphStyle('T', parent=styles['Title'], fontSize=15, textColor=colors.HexColor("#1A237E"))))
    elementos.append(Paragraph(f"Fecha Reporte: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elementos.append(Spacer(1, 15))
    
    if tipo == "PEDIDO":
        data = [["PACIENTE", "IDENTIFICACIÓN", "ENTIDAD", "FECHA TOMA", "mCi"]]
        for p in lista:
            if p['Estado'] not in ["CANCELADO", "DECAIMIENTO"]:
                f_toma = str(p.get('Fecha_Capsula', '')) if str(p.get('Fecha_Capsula', '')).lower() != 'nan' else ""
                data.append([p['Nombre'], p['ID'], p['Entidad'], f_toma, f"{p['mCI']}"])
        col_widths = [180, 100, 120, 80, 50]
    else:
        data = [["PACIENTE / ID", "ENTIDAD", "mCI", "ESTADO", "F. RECEPCIÓN", "F. ADMIN.", "OBSERVACIONES"]]
        for p in lista:
            f_recep = str(p.get('Fecha_Recepcion', '')) if str(p.get('Fecha_Recepcion', '')).lower() != 'nan' else ""
            f_admin = str(p.get('Fecha_Administracion', '')) if str(p.get('Fecha_Administracion', '')).lower() != 'nan' else ""
            obs = str(p.get('Notas', '')) if str(p.get('Notas', '')).lower() != 'nan' else ""
            data.append([
                Paragraph(f"<b>{p['Nombre']}</b><br/>{p['ID']}", styles['Normal']),
                p['Entidad'], p['mCI'], p['Estado'], f_recep, f_admin, Paragraph(obs, styles['Normal'])
            ])
        col_widths = [140, 90, 40, 80, 85, 85, 200]

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A237E")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTSIZE', (0, 0), (-1, -1), 8), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

t1, t2, t3 = st.tabs(["📋 Programación", "📦 Inventario", "🧮 Calculadora"])

with t1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            n, i, e = st.text_input("Nombre").upper(), st.text_input("Cédula"), st.text_input("Entidad").upper()
            d = st.number_input("Dosis mCi", 0.0)
            f = st.date_input("Fecha Toma de Cápsula").strftime("%d/%m/%Y")
            if st.form_submit_button("Sincronizar Pedido"):
                requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
                st.session_state.lista_local = cargar_datos(); st.rerun()
        st.divider()
        if st.button("🚨 LIMPIAR PANTALLA", use_container_width=True):
            requests.post(SCRIPT_URL); st.session_state.lista_local = []; st.rerun()
    with c2:
        if st.session_state.lista_local:
            df = pd.DataFrame(st.session_state.lista_local)
            # CONTADOR FUNDAMENTAL RESTAURADO
            total_mci = pd.to_numeric(df[~df['Estado'].isin(['CANCELADO', 'DECAIMIENTO'])]['mCI'], errors='coerce').sum()
            st.metric("Total mCi Pedido", f"{total_mci} mCi")
            st.download_button("📄 DESCARGAR PEDIDO", data=generar_pdf(st.session_state.lista_local, "PEDIDO"), file_name="pedido.pdf", use_container_width=True)
            st.dataframe(df[~df['Estado'].isin(['CANCELADO', 'DECAIMIENTO'])][["Nombre", "ID", "mCI", "Fecha_Capsula"]], use_container_width=True)

with t2:
    if st.session_state.lista_local:
        st.download_button("📑 REPORTE TRAZABILIDAD", data=generar_pdf(st.session_state.lista_local, "TRAZABILIDAD"), file_name="trazabilidad.pdf", use_container_width=True)
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                col_a, col_b = st.columns(2)
                est = col_a.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "ADMINISTRADA", "CANCELADO", "DECAIMIENTO"], index=0, key=f"s_{idx}")
                f_admin_val = col_a.date_input("Fecha Administración", key=f"fa_{idx}").strftime("%d/%m/%Y") if est == "ADMINISTRADA" else ""
                obs = col_a.text_area("Notas", value=str(p.get('Notas','')) if str(p.get('Notas',''))!='nan' else "", key=f"o_{idx}")
                if col_a.button("💾 Guardar", key=f"g_{idx}"):
                    requests.get(SCRIPT_URL, params={"action":"update", "old_id":str(p['ID']), "estado":est, "notas":obs, "fecha_administracion":f_admin_val})
                    st.session_state.lista_local = cargar_datos(); st.rerun()

with t3:
    st.header("🧮 Calculadora I-131")
    ai = st.number_input("Actividad Inicial (mCi)", value=100.0)
    fc = st.date_input("Fecha Calibración")
    ff = st.date_input("Fecha Cálculo")
    diff = (ff - fc).days * 24
    if diff >= 0:
        af = ai * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Actividad Final", f"{round(af, 2)} mCi")
