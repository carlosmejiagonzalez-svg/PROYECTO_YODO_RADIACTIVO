import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# URL de tu Script
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

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

def generar_pdf_detallado(lista, titulo_reporte):
    buffer = io.BytesIO()
    # Usamos landscape (apaisado) para que quepa toda la información de trazabilidad
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elementos = []
    styles = getSampleStyleSheet()
    
    # Estilo de Título Moderno
    title_style = ParagraphStyle('ModernTitle', parent=styles['Title'], fontSize=18, textColor=colors.HexColor("#1A237E"), spaceAfter=10)
    subtitle_style = ParagraphStyle('ModernSub', parent=styles['Normal'], fontSize=10, textColor=colors.grey)

    elementos.append(Paragraph(f"<b>{titulo_reporte}</b>", title_style))
    elementos.append(Paragraph(f"NUCLEAR 2000 LTDA - Registro de Control y Trazabilidad de Radionúclidos", subtitle_style))
    elementos.append(Paragraph(f"Fecha de emisión: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elementos.append(Spacer(1, 20))
    
    # Encabezados detallados
    data = [["PACIENTE / ID", "ENTIDAD", "DOSIS", "ESTADO", "RECEPCIÓN", "OBSERVACIONES Y TRAZABILIDAD"]]
    
    for p in lista:
        # Limpieza de notas para el PDF
        nota = str(p['Notas']) if str(p['Notas']).lower() != 'nan' else "Sin observaciones"
        data.append([
            Paragraph(f"<b>{p['Nombre']}</b><br/>ID: {p['ID']}", styles['Normal']),
            p['Entidad'],
            f"{p['mCI']} mCi",
            p['Estado'],
            p['Fecha_Recepcion'] if p['Fecha_Recepcion'] else "---",
            Paragraph(nota, styles['Normal'])
        ])
    
    # Tabla con diseño estético
    t = Table(data, colWidths=[150, 100, 60, 80, 100, 240])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A237E")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
    ]))
    
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

t1, t2, t3 = st.tabs(["📋 Programación de Pedidos", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- TAB 1: PROGRAMACIÓN ---
with t1:
    col_f, col_v = st.columns([1, 2])
    with col_f:
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            n = st.text_input("Nombre").upper()
            i = st.text_input("Cédula")
            e = st.text_input("Entidad").upper()
            d = st.number_input("Dosis (mCi)", 0.0)
            f = st.date_input("Fecha Aplicación").strftime("%d/%m/%Y")
            if st.form_submit_button("Sincronizar Pedido"):
                requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
                st.session_state.lista_local = cargar_datos()
                st.rerun()
        
        if st.button("🚨 REINICIAR SEMANA (BORRAR TODO)", use_container_width=True):
            requests.post(SCRIPT_URL)
            st.session_state.lista_local = []
            st.rerun()

    with col_v:
        st.subheader("📊 Resumen de Programación")
        if st.session_state.lista_local:
            # BOTÓN PDF RESTAURADO EN PESTAÑA 1
            pdf_pedidos = generar_pdf_detallado(st.session_state.lista_local, "REPORTE DE PEDIDOS")
            st.download_button("📄 DESCARGAR PEDIDO PDF", data=pdf_pedidos, file_name="pedido_semanal.pdf", use_container_width=True)
            
            df = pd.DataFrame(st.session_state.lista_local)
            prog = df[df['Estado'] != 'CANCELADO']['mCI'].apply(pd.to_numeric).sum()
            st.metric("Total mCi Programados", f"{prog} mCi")
            st.dataframe(df[["Nombre", "ID", "mCI", "Estado"]], use_container_width=True)

# --- TAB 2: INVENTARIO ---
with t2:
    if st.session_state.lista_local:
        ct, cb = st.columns([2, 1])
        ct.header("Gestión de Trazabilidad")
        
        # BOTÓN REPORTE DETALLADO (RESUMEN GENERAL)
        pdf_total = generar_pdf_detallado(st.session_state.lista_local, "HOJA DE TRAZABILIDAD Y MOVIMIENTO")
        cb.download_button("📑 GENERAR REPORTE DETALLADO (PDF)", data=pdf_total, file_name="trazabilidad_detallada.pdf", use_container_width=True)

        for idx, p in enumerate(st.session_state.lista_local):
            color_edo = "green" if p['Estado'] == "APLICADO" else "orange" if p['Estado'] == "RECIBIDO" else "red" if p['Estado'] == "CANCELADO" else "blue"
            with st.expander(f"📌 {p['Nombre']} | {p['Estado']}"):
                col1, col2 = st.columns(2)
                
                nuevo_est = col1.selectbox("Cambiar Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"], 
                                         index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"].index(p.get('Estado', 'PENDIENTE')), key=f"est_{idx}")
                
                v_notas = str(p.get('Notas', '')) if str(p.get('Notas', '')).lower() != 'nan' else ""
                nuevas_notas = col1.text_area("Observaciones / Motivo", value=v_notas, key=f"obs_{idx}", help="Si cancela, escriba aquí el motivo.")
                
                if col1.button("💾 Guardar Cambios", key=f"sav_{idx}"):
                    requests.get(SCRIPT_URL, params={"action":"update", "old_id":str(p['ID']).strip(), "estado":nuevo_est, "notas":nuevas_notas})
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                if p.get('Estado') == "CANCELADO":
                    col2.error("🔄 Reasignación de Dosis")
                    rn = col2.text_input("Nombre Nuevo Paciente", key=f"rn_{idx}").upper()
                    ri = col2.text_input("ID Nuevo Paciente", key=f"ri_{idx}")
                    re = col2.text_input("Entidad", value=p['Entidad'], key=f"re_{idx}").upper()
                    
                    if col2.button("Confirmar Traspaso", key=f"tr_{idx}"):
                        hist_text = f"CEDIDA POR: {p['Nombre']} (ID: {p['ID']}). MOTIVO: {nuevas_notas}"
                        params = {
                            "action": "reasignar", "old_id": str(p['ID']).strip(),
                            "nombre": rn, "id": ri, "entidad": re,
                            "mci": p['mCI'], "fecha": p['Fecha_Capsula'], "notas": hist_text
                        }
                        requests.get(SCRIPT_URL, params=params)
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()

# --- TAB 3: CALCULADORA ---
with t3:
    st.header("🧮 Calculadora de Decaimiento I-131")
    c1, c2 = st.columns(2)
    with c1:
        act_i = st.number_input("Actividad Inicial (mCi)", value=100.0)
        f_cal = st.date_input("Fecha Calibración")
        h_cal = st.time_input("Hora Calibración")
    with c2:
        f_fut = st.date_input("Fecha Cálculo")
        h_fut = st.time_input("Hora Cálculo")
    
    dt1 = datetime.combine(f_cal, h_cal)
    dt2 = datetime.combine(f_fut, h_fut)
    diff = (dt2 - dt1).total_seconds() / 3600
    if diff >= 0:
        act_f = act_i * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Resultado Actividad", f"{round(act_f, 2)} mCi", help="Fórmula de decaimiento radiactivo")
    else: st.warning("La fecha de cálculo debe ser posterior.")
