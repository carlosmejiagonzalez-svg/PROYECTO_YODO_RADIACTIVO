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

# Configuración
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
            columnas = ["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI", "Estado", "Fecha_Recepcion", "mCI_Real", "Notas"]
            for c in columnas:
                if c not in df.columns: df[c] = ""
            return df.to_dict('records')
    except: pass
    return []

def generar_pdf(lista, tipo="PEDIDO"):
    buffer = io.BytesIO()
    orientacion = letter if tipo == "PEDIDO" else landscape(letter)
    doc = SimpleDocTemplate(buffer, pagesize=orientacion, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    styles = getSampleStyleSheet()
    
    if os.path.exists(LOGO_PATH):
        try:
            img = Image(LOGO_PATH, width=100, height=50)
            img.hAlign = 'LEFT'
            elementos.append(img)
        except: pass
    
    titulo_texto = "PEDIDO DE RADIOFÁRMACOS" if tipo == "PEDIDO" else "REPORTE DE TRAZABILIDAD Y MOVIMIENTO"
    elementos.append(Paragraph(f"<b>{titulo_texto}</b>", ParagraphStyle('T', parent=styles['Title'], fontSize=16, textColor=colors.HexColor("#1A237E"), spaceAfter=5)))
    elementos.append(Paragraph("<b>NUCLEAR 2000 LTDA</b>", styles['Normal']))
    elementos.append(Paragraph(f"Fecha: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elementos.append(Spacer(1, 15))
    
    if tipo == "PEDIDO":
        data = [["PACIENTE", "IDENTIFICACIÓN", "ENTIDAD", "DOSIS (mCi)"]]
        for p in lista:
            if p['Estado'] not in ["CANCELADO", "DECAIMIENTO"]:
                data.append([p['Nombre'], p['ID'], p['Entidad'], f"{p['mCI']}"])
        col_widths = [200, 110, 130, 80]
    else:
        # Columna de recepción ahora muestra también fecha de administración
        data = [["PACIENTE / ID", "ENTIDAD", "mCI", "ESTADO", "RECEPCIÓN / ADMIN.", "HISTORIAL / MOTIVOS"]]
        for p in lista:
            hist = str(p['Notas']) if str(p['Notas']).lower() != 'nan' else ""
            data.append([
                Paragraph(f"<b>{p['Nombre']}</b><br/>ID: {p['ID']}", styles['Normal']),
                p['Entidad'], p['mCI'], p['Estado'], p['Fecha_Recepcion'],
                Paragraph(hist, styles['Normal'])
            ])
        col_widths = [140, 90, 50, 80, 100, 230]

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A237E")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")])
    ]))
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

t1, t2, t3 = st.tabs(["📋 Programación (Pedido)", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- TAB 1 ---
with t1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            n, i, e = st.text_input("Nombre").upper(), st.text_input("Cédula"), st.text_input("Entidad").upper()
            d, f = st.number_input("Dosis mCi", 0.0), st.date_input("Fecha").strftime("%d/%m/%Y")
            if st.form_submit_button("Sincronizar Pedido"):
                requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
                st.session_state.lista_local = cargar_datos(); st.rerun()
        if st.button("🚨 REINICIAR LISTA"):
            requests.post(SCRIPT_URL); st.session_state.lista_local = []; st.rerun()
    with c2:
        st.subheader("📊 Pedido de la Semana")
        if st.session_state.lista_local:
            df = pd.DataFrame(st.session_state.lista_local)
            prog = df[~df['Estado'].isin(['CANCELADO', 'DECAIMIENTO'])]['mCI'].apply(pd.to_numeric).sum()
            st.metric("Total mCi Activos", f"{prog} mCi")
            st.download_button("📄 DESCARGAR PEDIDO PDF", data=generar_pdf(st.session_state.lista_local, "PEDIDO"), file_name="pedido.pdf", use_container_width=True)
            st.dataframe(df[~df['Estado'].isin(['CANCELADO', 'DECAIMIENTO'])][["Nombre", "ID", "Entidad", "mCI"]], use_container_width=True)

# --- TAB 2 ---
with t2:
    if st.session_state.lista_local:
        col_t, col_b = st.columns([2, 1])
        col_t.header("Trazabilidad Detallada")
        col_b.download_button("📑 GENERAR REPORTE TRAZABILIDAD", data=generar_pdf(st.session_state.lista_local, "TRAZABILIDAD"), file_name="trazabilidad.pdf", use_container_width=True)
        
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                col_a, col_b = st.columns(2)
                # CAMBIO: "ADMINISTRADA" en lugar de "APLICADA"
                est_list = ["PENDIENTE", "RECIBIDO", "ADMINISTRADA", "CANCELADO", "DECAIMIENTO"]
                est = col_a.selectbox("Estado", est_list, 
                                    index=est_list.index(p.get('Estado', 'PENDIENTE')), key=f"s_{idx}")
                
                # FECHA DE ADMINISTRACIÓN (Solo aparece si selecciona ADMINISTRADA)
                fecha_admin = p.get('Fecha_Recepcion', '')
                if est == "ADMINISTRADA":
                    fecha_admin = col_a.date_input("Fecha de Administración", key=f"fa_{idx}").strftime("%d/%m/%Y")
                
                obs = col_a.text_area("Notas", value=str(p.get('Notas','')) if str(p.get('Notas',''))!='nan' else "", key=f"o_{idx}")
                
                if col_a.button("💾 Guardar", key=f"g_{idx}"):
                    # Se envía la fecha_admin al campo Fecha_Recepcion en la hoja de cálculo
                    requests.get(SCRIPT_URL, params={"action":"update", "old_id":str(p['ID']).strip(), "estado":est, "notas":obs, "fecha":fecha_admin})
                    st.session_state.lista_local = cargar_datos(); st.rerun()
                
                if p.get('Estado') == "CANCELADO":
                    col_b.warning("🔄 Reasignación")
                    rn, ri = col_b.text_input("Nuevo Nombre", key=f"rn_{idx}").upper(), col_b.text_input("Nueva Cédula", key=f"ri_{idx}")
                    re, rd = col_b.text_input("Nueva Entidad", value=p['Entidad'], key=f"re_{idx}").upper(), col_b.number_input("Nueva Dosis (mCi)", value=float(p['mCI']), key=f"rd_{idx}")
                    if col_b.button("Confirmar Traspaso", key=f"tr_{idx}"):
                        h = f"Dosis cedida por: {p['Nombre']}. Motivo: {obs}"
                        requests.get(SCRIPT_URL, params={"action":"reasignar", "old_id":str(p['ID']).strip(), "nombre":rn, "id":ri, "entidad":re, "mci":rd, "fecha":p['Fecha_Capsula'], "notas":h})
                        st.session_state.lista_local = cargar_datos(); st.rerun()

# --- TAB 3 ---
with t3:
    st.header("🧮 Calculadora de Decaimiento I-131")
    col1, col2 = st.columns(2)
    ai = col1.number_input("Actividad Inicial (mCi)", value=100.0)
    fc, hc = col1.date_input("Fecha Calibración"), col1.time_input("Hora Calibración")
    ff, hf = col2.date_input("Fecha Cálculo"), col2.time_input("Hora Cálculo")
    dt1, dt2 = datetime.combine(fc, hc), datetime.combine(ff, hf)
    diff = (dt2 - dt1).total_seconds() / 3600
    if diff >= 0:
        af = ai * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Actividad Final", f"{round(af, 2)} mCi")
    else: st.error("La fecha debe ser posterior.")
