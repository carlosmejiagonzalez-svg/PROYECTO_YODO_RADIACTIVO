import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import math
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
import os
from streamlit_gsheets import GSheetsConnection

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda - Gestión Avanzada", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
LIMITE_SEMANAL = 150.0
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_desde_drive():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df.to_dict('records')
    except: pass
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos_desde_drive()

def calcular_decaimiento(actividad_inicial, horas_transcurridas):
    hl_horas = HL_YODO * 24
    return actividad_inicial * math.exp(-math.log(2) * horas_transcurridas / hl_horas)

def generar_pdf(lista, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    logo_path = "logo.png" 
    if os.path.exists(logo_path):
        img = Image(logo_path, width=120, height=60)
        img.hAlign = 'CENTER'
        elementos.append(img); elementos.append(Spacer(1, 10))
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES - YODO 131</b>", estilos['Title']))
    elementos.append(Paragraph("<font size=12>Nuclear 2000 Ltda</font>", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for p in lista:
        f_val = p.get('Fecha') or ""
        data.append([p.get('Nombre',''), p.get('ID',''), p.get('Entidad',''), f_val, p.get('mCI', 0)])
    tabla = Table(data, colWidths=[160, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.darkblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey),('ALIGN',(0,0),(-1,-1),'CENTER')]))
    elementos.append(tabla); elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS PROGRAMADA: {total} mCi</b>", estilos['Normal']))
    doc.build(elementos); buffer.seek(0)
    return buffer

st.title("☢️ Gestión de Medicina Nuclear - Nuclear 2000 Ltda")
tab1, tab2, tab3 = st.tabs(["📋 Programación", "📦 Inventario", "🧮 Calculadora"])

dosis_actual = sum(float(p.get('mCI', 0)) for p in st.session_state.lista_local)
restante = LIMITE_SEMANAL - dosis_actual

# --- TAB 1: PROGRAMACIÓN ---
with tab1:
    with st.sidebar.form("registro", clear_on_submit=True):
        st.header("Registrar Paciente")
        nombre = st.text_input("Nombre").upper()
        cedula = st.text_input("ID")
        entidad = st.text_input("Entidad").upper()
        dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
        fecha = st.date_input("Fecha de Aplicación", value=datetime.now(colombia_tz))
        if st.form_submit_button("Sincronizar Pedido"):
            if nombre and cedula:
                fecha_str = fecha.strftime("%d/%m/%Y")
                params = {"action": "register", "nombre": nombre, "id": cedula, "entidad": entidad, "fecha": fecha_str, "mci": dosis}
                st.session_state.lista_local.append({"Nombre": nombre, "ID": cedula, "Entidad": entidad, "Fecha": fecha_str, "mCI": dosis, "Estado": "PENDIENTE", "Notas": ""})
                requests.get(SCRIPT_URL, params=params, timeout=5)
                st.rerun()
    st.metric("Total Programado", f"{round(dosis_actual, 2)} mCi")
    if st.session_state.lista_local:
        st.dataframe(pd.DataFrame(st.session_state.lista_local)[["Nombre", "ID", "Entidad", "Fecha", "mCI", "Estado"]], use_container_width=True)
        if st.button("🚨 LIMPIAR SEMANA", type="primary"):
            requests.post(SCRIPT_URL, timeout=10)
            st.session_state.lista_local = []; st.rerun()

# --- TAB 2: INVENTARIO ---
with tab2:
    st.header("Gestión de Dosis")
    for idx, p in enumerate(st.session_state.lista_local):
        with st.expander(f"📍 {p['Nombre']} - {p['mCI']} mCi [{p['Estado']}]"):
            c_est, c_reas = st.columns(2)
            
            # Cambio de Estado y Notas
            nuevo_estado = c_est.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"], index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"].index(p['Estado']), key=f"st_{idx}")
            nuevas_notas = c_est.text_area("Notas / Observaciones", value=p.get('Notas', ""), key=f"nt_{idx}")
            
            if c_est.button("💾 Guardar Cambios", key=f"btn_save_{idx}"):
                params = {"action": "update", "id": p['ID'], "nombre": p['Nombre'], "estado": nuevo_estado, "mci": p['mCI'], "notas": nuevas_notas}
                requests.get(SCRIPT_URL, params=params, timeout=5)
                st.session_state.lista_local[idx]['Estado'] = nuevo_estado
                st.session_state.lista_local[idx]['Notas'] = nuevas_notas
                st.success("Sincronizado con Drive"); st.rerun()

            # Reasignación
            if p['Estado'] == "CANCELADO":
                c_reas.info("Reasignar esta dosis:")
                n_nom = c_reas.text_input("Nuevo Paciente", key=f"nn_{idx}").upper()
                n_mci = c_reas.number_input("Dosis a dar (mCi)", value=float(p['mCI']), key=f"nmci_{idx}")
                if c_reas.button("🔄 Confirmar Reasignación", key=f"br_{idx}"):
                    # Al reasignar, actualizamos nombre y dosis en la misma fila del ID original
                    params = {"action": "update", "id": p['ID'], "nombre": n_nom, "estado": "RECIBIDO", "mci": n_mci, "notas": f"Reasignado (Original: {p['Nombre']})"}
                    requests.get(SCRIPT_URL, params=params, timeout=5)
                    st.session_state.lista_local[idx].update({"Nombre": n_nom, "mCI": n_mci, "Estado": "RECIBIDO", "Notas": f"Reasignado de {p['Nombre']}"})
                    st.rerun()

# --- TAB 3: CALCULADORA ---
with tab3:
    st.header("Calculadora de Decaimiento")
    col1, col2 = st.columns(2)
    act_inicial = col1.number_input("Actividad Inicial (mCi)", 0.0, 500.0, 50.0)
    fecha_cal = col1.date_input("Fecha de calibración", datetime.now(colombia_tz)) # Cambio solicitado
    hora_cal = col1.time_input("Hora de calibración")
    
    fecha_f = col2.date_input("Fecha a Consultar", datetime.now(colombia_tz))
    hora_f = col2.time_input("Hora a Consultar")
    
    dt_i = datetime.combine(fecha_cal, hora_cal)
    dt_f = datetime.combine(fecha_f, hora_f)
    diff = (dt_f - dt_i).total_seconds() / 3600
    
    if diff >= 0:
        res = calcular_decaimiento(act_inicial, diff)
        st.metric("Actividad Resultante", f"{round(res, 2)} mCi")
    else: st.error("La fecha de consulta debe ser posterior.")
