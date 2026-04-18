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
            # Aseguramos que existan las columnas necesarias
            columnas = ["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI", "Estado", "Fecha_Recepcion", "mCI_Real", "Notas"]
            for c in columnas:
                if c not in df.columns: df[c] = ""
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
            img = Image(LOGO_PATH, width=80, height=40)
            img.hAlign = 'LEFT'
            elementos.append(img)
        except: pass
    
    titulo_texto = "PEDIDO DE RADIOFÁRMACOS" if tipo == "PEDIDO" else "REPORTE DE TRAZABILIDAD Y MOVIMIENTO"
    elementos.append(Paragraph(f"<b>{titulo_texto}</b>", ParagraphStyle('T', parent=styles['Title'], fontSize=15, textColor=colors.HexColor("#1A237E"))))
    elementos.append(Paragraph(f"Fecha Reporte: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elementos.append(Spacer(1, 15))
    
    if tipo == "PEDIDO":
        data = [["PACIENTE", "IDENTIFICACIÓN", "ENTIDAD", "DOSIS (mCi)"]]
        for p in lista:
            if p['Estado'] not in ["CANCELADO", "DECAIMIENTO"]:
                data.append([p['Nombre'], p['ID'], p['Entidad'], f"{p['mCI']}"])
        col_widths = [210, 110, 130, 80]
    else:
        # REPORTE DETALLADO CON AMBAS FECHAS
        data = [["PACIENTE / ID", "ENTIDAD", "mCI", "ESTADO", "F. RECEPCIÓN", "F. ADMIN.", "OBSERVACIONES"]]
        for p in lista:
            txt_notas = str(p['Notas']) if str(p['Notas']).lower() != 'nan' else ""
            # Si el estado es administrada, solemos guardar la fecha de admin en mCI_Real o similar, 
            # pero aquí asumiremos que tu hoja tiene columnas para ambas.
            f_recep = str(p['Fecha_Recepcion']) if str(p['Fecha_Recepcion']).lower() != 'nan' else ""
            f_admin = str(p['mCI_Real']) if str(p['mCI_Real']).lower() != 'nan' else "" # Usamos mCI_Real como campo temporal para f_admin si no hay otro
            
            data.append([
                Paragraph(f"<b>{p['Nombre']}</b><br/>{p['ID']}", styles['Normal']),
                p['Entidad'], p['mCI'], p['Estado'], f_recep, f_admin,
                Paragraph(txt_notas, styles['Normal'])
            ])
        col_widths = [140, 90, 40, 80, 85, 85, 200]

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A237E")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")])
    ]))
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

t1, t2, t3 = st.tabs(["📋 Programación", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- TAB 1 ---
with t1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            n, i, e = st.text_input("Nombre").upper(), st.text_input("Cédula"), st.text_input("Entidad").upper()
            d, f = st.number_input("Dosis mCi", 0.0), st.date_input("Fecha Pedido").strftime("%d/%m/%Y")
            if st.form_submit_button("Sincronizar"):
                requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
                st.session_state.lista_local = cargar_datos(); st.rerun()

    with c2:
        if st.session_state.lista_local:
            df = pd.DataFrame(st.session_state.lista_local)
            st.download_button("📄 DESCARGAR PEDIDO", data=generar_pdf(st.session_state.lista_local, "PEDIDO"), file_name="pedido.pdf")
            st.dataframe(df[~df['Estado'].isin(['CANCELADO', 'DECAIMIENTO'])][["Nombre", "ID", "mCI"]], use_container_width=True)

# --- TAB 2 ---
with t2:
    if st.session_state.lista_local:
        st.download_button("📑 REPORTE TRAZABILIDAD COMPLETO", data=generar_pdf(st.session_state.lista_local, "TRAZABILIDAD"), file_name="trazabilidad.pdf")
        
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                col_a, col_b = st.columns(2)
                
                est_list = ["PENDIENTE", "RECIBIDO", "ADMINISTRADA", "CANCELADO", "DECAIMIENTO"]
                est = col_a.selectbox("Estado", est_list, index=est_list.index(p.get('Estado', 'PENDIENTE')), key=f"s_{idx}")
                
                # FECHAS
                f_recep_val = col_a.text_input("Fecha Recepción", value=str(p.get('Fecha_Recepcion', '')), key=f"fr_{idx}")
                
                f_admin_val = str(p.get('mCI_Real', '')) # Usamos mCI_Real para guardar la fecha de admin
                if est == "ADMINISTRADA":
                    f_admin_val = col_a.date_input("Fecha de Administración", key=f"fa_{idx}").strftime("%d/%m/%Y")
                
                obs = col_a.text_area("Notas / Motivo", value=str(p.get('Notas','')) if str(p.get('Notas',''))!='nan' else "", key=f"o_{idx}")
                
                if col_a.button("💾 Guardar", key=f"g_{idx}"):
                    # Enviamos ambos campos de fecha al script
                    requests.get(SCRIPT_URL, params={
                        "action": "update", 
                        "old_id": str(p['ID']).strip(), 
                        "estado": est, 
                        "notas": obs, 
                        "fecha": f_recep_val,    # Fecha de llegada
                        "mci_real": f_admin_val  # Fecha de aplicación
                    })
                    st.session_state.lista_local = cargar_datos(); st.rerun()

# --- TAB 3 ---
with t3:
    st.header("🧮 Calculadora")
    # Lógica de calculadora...
    c1, c2 = st.columns(2)
    ai = c1.number_input("Actividad Inicial", value=100.0)
    dt1 = datetime.combine(c1.date_input("F. Calibración"), c1.time_input("H. Calibración"))
    dt2 = datetime.combine(c2.date_input("F. Cálculo"), c2.time_input("H. Cálculo"))
    diff = (dt2 - dt1).total_seconds() / 3600
    if diff >= 0:
        af = ai * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Actividad Final", f"{round(af, 2)} mCi")
