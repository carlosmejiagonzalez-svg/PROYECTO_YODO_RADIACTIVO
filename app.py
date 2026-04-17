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

st.set_page_config(page_title="Nuclear 2000 Ltda - Gestión Integral", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            # Asegurar que todas las columnas necesarias existan en el DataFrame
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
    
    # Logo
    if os.path.exists("logo.png"):
        img = Image("logo.png", width=100, height=50)
        img.hAlign = 'LEFT'
        elementos.append(img)
    
    elementos.append(Paragraph("<b>REPORTE FINAL DE TRAZABILIDAD DE DOSIS</b>", estilos['Title']))
    elementos.append(Paragraph(f"Fecha de reporte: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    # Tabla de datos
    data = [["Paciente / ID", "Entidad", "Dosis", "Estado", "Recibido el", "Observaciones"]]
    for p in lista:
        paciente_id = f"{p.get('Nombre','')}\nID: {p.get('ID','')}"
        data.append([
            paciente_id, 
            p.get('Entidad',''), 
            f"{p.get('mCI','')} mCi", 
            p.get('Estado',''),
            p.get('Fecha_Recepcion',''),
            p.get('Notas','')
        ])
    
    tabla = Table(data, colWidths=[130, 80, 50, 70, 90, 120])
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.black),
        ('FONTSIZE',(0,0),(-1,-1),8),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

st.title("☢️ Gestión de Medicina Nuclear - Nuclear 2000 Ltda")
tab1, tab2, tab3 = st.tabs(["📋 Programación", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- TAB 1: REGISTRO ---
with tab1:
    with st.sidebar.form("registro", clear_on_submit=True):
        st.header("Ingreso de Pedido")
        n = st.text_input("Nombre").upper()
        i = st.text_input("ID")
        e = st.text_input("Entidad").upper()
        d = st.number_input("mCi", 0.0, step=0.1)
        if st.form_submit_button("Registrar en Pedido"):
            if n and i:
                params = {"action": "register", "nombre": n, "id": i, "entidad": e, "mci": d, "fecha": datetime.now(colombia_tz).strftime("%d/%m/%Y")}
                requests.get(SCRIPT_URL, params=params, timeout=10)
                st.session_state.lista_local = cargar_datos()
                st.rerun()

    if st.session_state.lista_local:
        st.dataframe(pd.DataFrame(st.session_state.lista_local)[["Nombre", "ID", "Entidad", "mCI", "Estado"]], use_container_width=True)
        if st.button("🚨 BORRAR SEMANA (RESETEAR)"):
            requests.post(SCRIPT_URL, timeout=10)
            st.session_state.lista_local = []
            st.rerun()

# --- TAB 2: GESTIÓN Y REPORTE ---
with tab2:
    col_rep1, col_rep2 = st.columns([2,1])
    col_rep1.header("Gestión de Dosis Recibidas")
    
    if st.session_state.lista_local:
        # BOTÓN DE REPORTE SEMANAL
        reporte_pdf = generar_reporte_trazabilidad(st.session_state.lista_local)
        col_rep2.download_button(
            label="📄 GENERAR REPORTE SEMANAL",
            data=reporte_pdf,
            file_name=f"trazabilidad_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        for idx, p in enumerate(st.session_state.lista_local):
            # El expander ahora es más informativo
            with st.expander(f"📌 {p['Nombre']} | Estado: {p.get('Estado','PENDIENTE')}"):
                c1, c2 = st.columns(2)
                
                # Actualización de Estado
                n_est = c1.selectbox("Cambiar Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"], 
                                   index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"].index(p.get('Estado', 'PENDIENTE')),
                                   key=f"sel_{idx}")
                n_not = c1.text_area("Observaciones", value=p.get('Notas', ""), key=f"not_{idx}")
                
                if c1.button("💾 Guardar y Cerrar", key=f"save_{idx}"):
                    params = {"action": "update", "old_id": p['ID'], "id": p['ID'], "nombre": p['Nombre'], "entidad": p['Entidad'], "estado": n_est, "mci": p['mCI'], "notas": n_not}
                    requests.get(SCRIPT_URL, params=params, timeout=15)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun() # Esto cierra automáticamente el expander al recargar

                # Reasignación
                if p.get('Estado') == "CANCELADO":
                    c2.info("Formulario de Reasignación")
                    rn = c2.text_input("Nuevo Nombre", key=f"rn_{idx}").upper()
                    ri = c2.text_input("Nueva ID", key=f"ri_{idx}")
                    re = c2.text_input("Nueva Entidad", key=f"re_{idx}").upper()
                    rd = c2.number_input("Nueva Dosis", value=float(p['mCI']), key=f"rd_{idx}")
                    
                    if c2.button("🔄 Confirmar Reasignación", key=f"br_{idx}"):
                        params = {"action": "update", "old_id": p['ID'], "id": ri, "nombre": rn, "entidad": re, "estado": "RECIBIDO", "mci": rd, "notas": f"REASIGNADO (Anterior: {p['Nombre']})"}
                        requests.get(SCRIPT_URL, params=params, timeout=15)
                        st.session_state.lista_local = cargar_datos()
                        st.rerun() # Cierra el expander

# --- TAB 3: CALCULADORA ---
with tab3:
    st.header("Cálculo de Decaimiento")
    c_cal1, c_cal2 = st.columns(2)
    a_ini = c_cal1.number_input("Dosis Inicial (mCi)", 0.0, value=50.0)
    f_cal = c_cal1.date_input("Fecha calibración")
    h_cal = c_cal1.time_input("Hora calibración")
    f_fut = c_cal2.date_input("Fecha consulta")
    h_fut = c_cal2.time_input("Hora consulta")
    
    dt_i = datetime.combine(f_cal, h_cal)
    dt_f = datetime.combine(f_fut, h_fut)
    diff = (dt_f - dt_i).total_seconds() / 3600
    
    if diff >= 0:
        a_fin = a_ini * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Resultado", f"{round(a_fin, 2)} mCi")
    else: st.error("La fecha debe ser posterior")
