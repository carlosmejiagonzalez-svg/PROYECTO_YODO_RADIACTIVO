import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
import os
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# URL de tu Script
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda - Trazabilidad Avanzada", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            cols_necesarias = ["Nombre", "ID", "Entidad", "Fecha", "mCI", "Estado", "Fecha_Recepcion", "Notas"]
            for c in cols_necesarias:
                if c not in df.columns: df[c] = ""
            return df.to_dict('records')
    except: pass
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

def generar_reporte_trazabilidad(lista):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    
    if os.path.exists("logo.png"):
        img = Image("logo.png", width=100, height=50)
        img.hAlign = 'LEFT'
        elementos.append(img)
    
    elementos.append(Paragraph("<b>REPORTE DE TRAZABILIDAD Y GESTIÓN DE DOSIS</b>", estilos['Title']))
    elementos.append(Paragraph(f"Generado: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    data = [["Paciente / ID", "Entidad", "Dosis", "Estado", "Recibido el", "Historial Completo"]]
    for p in lista:
        paciente_info = f"{p.get('Nombre','')}\nID: {p.get('ID','')}"
        data.append([
            paciente_info, 
            p.get('Entidad',''), 
            f"{p.get('mCI','')} mCi", 
            p.get('Estado',''),
            p.get('Fecha_Recepcion',''),
            p.get('Notas','') # Aquí saldrá todo el detalle del original
        ])
    
    tabla = Table(data, colWidths=[120, 70, 50, 70, 90, 160])
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),7),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

st.title("☢️ Sistema Nuclear - Nuclear 2000 Ltda")
tab1, tab2, tab3 = st.tabs(["📋 Programación", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- TAB 1: PROGRAMACIÓN ---
with tab1:
    with st.sidebar.form("registro", clear_on_submit=True):
        st.header("Nuevo Pedido")
        n = st.text_input("Nombre").upper()
        i = st.text_input("ID")
        e = st.text_input("Entidad").upper()
        d = st.number_input("mCi", 0.0)
        if st.form_submit_button("Registrar en Pedido"):
            if n and i:
                params = {"action": "register", "nombre": n, "id": i, "entidad": e, "mci": d, "fecha": datetime.now(colombia_tz).strftime("%d/%m/%Y")}
                requests.get(SCRIPT_URL, params=params, timeout=10)
                st.session_state.lista_local = cargar_datos()
                st.rerun()

    if st.session_state.lista_local:
        df_prog = pd.DataFrame(st.session_state.lista_local)
        st.dataframe(df_prog[["Nombre", "ID", "Entidad", "mCI", "Estado"]], use_container_width=True)
        if st.button("🚨 REINICIAR SEMANA"):
            requests.post(SCRIPT_URL, timeout=10)
            st.session_state.lista_local = []
            st.rerun()

# --- TAB 2: INVENTARIO Y REPORTE ---
with tab2:
    c_h, c_r = st.columns([2,1])
    c_h.header("Control de Dosis y Trazabilidad")
    
    if st.session_state.lista_local:
        pdf_file = generar_reporte_trazabilidad(st.session_state.lista_local)
        c_r.download_button("📄 DESCARGAR REPORTE FINAL", data=pdf_file, 
                           file_name=f"reporte_nuclear_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
                           use_container_width=True)

        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | Estado: {p.get('Estado','PENDIENTE')}"):
                col1, col2 = st.columns(2)
                
                # Gestión Manual
                n_est = col1.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"], 
                                     index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"].index(p.get('Estado', 'PENDIENTE')),
                                     key=f"sel_{idx}")
                n_not = col1.text_area("Motivo de Cancelación / Notas", value=p.get('Notas', ""), key=f"not_{idx}")
                
                if col1.button("💾 Guardar y Cerrar", key=f"sv_{idx}"):
                    params = {"action": "update", "old_id": p['ID'], "id": p['ID'], "nombre": p['Nombre'], "entidad": p['Entidad'], "estado": n_est, "mci": p['mCI'], "notas": n_not}
                    requests.get(SCRIPT_URL, params=params, timeout=15)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                # REASIGNACIÓN CON TRAZABILIDAD TOTAL
                if p.get('Estado') == "CANCELADO":
                    col2.warning("Reasignar dosis de este paciente")
                    rn = col2.text_input("Nombre Nuevo Paciente", key=f"rn_{idx}").upper()
                    ri = col2.text_input("Nueva ID", key=f"ri_{idx}")
                    re = col2.text_input("Nueva Entidad", key=f"re_{idx}").upper()
                    rd = col2.number_input("Dosis (mCi)", value=float(p['mCI']), key=f"rd_{idx}")
                    
                    if col2.button("🔄 Ejec
