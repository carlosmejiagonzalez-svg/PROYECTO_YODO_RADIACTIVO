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

# URL de tu Script (Asegúrate de haber implementado la última versión en Apps Script)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda - Trazabilidad", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            columnas = ["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI", "Estado", "Fecha_Recepcion", "mCI_Real", "Notas"]
            for c in columnas:
                if c not in df.columns: df[c] = ""
            return df.to_dict('records')
    except: pass
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

def generar_pdf(lista):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    elementos.append(Paragraph("<b>REPORTE DE TRAZABILIDAD - NUCLEAR 2000 LTDA</b>", estilos['Title']))
    elementos.append(Paragraph(f"Fecha: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    data = [["Paciente/ID", "Entidad", "mCI", "Estado", "Recibido", "Historial"]]
    for p in lista:
        data.append([f"{p['Nombre']}\n{p['ID']}", p['Entidad'], p['mCI'], p['Estado'], p['Fecha_Recepcion'], p['Notas']])
    
    t = Table(data, colWidths=[120, 80, 50, 70, 90, 150])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.darkblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),7)]))
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

st.title("☢️ Gestión de Medicina Nuclear - Nuclear 2000 Ltda")
tab1, tab2, tab3 = st.tabs(["📋 Programación", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- TAB 1: PROGRAMACIÓN (Botones recuperados) ---
with tab1:
    with st.sidebar.form("registro", clear_on_submit=True):
        st.header("Ingreso de Pedido")
        n = st.text_input("Nombre").upper()
        i = st.text_input("ID")
        e = st.text_input("Entidad").upper()
        d = st.number_input("mCI", 0.0)
        f = st.date_input("Fecha Aplicación").strftime("%d/%m/%Y")
        if st.form_submit_button("Sincronizar Pedido"):
            if n and i:
                params = {"action": "register", "nombre": n, "id": i, "entidad": e, "mci": d, "fecha": f}
                requests.get(SCRIPT_URL, params=params, timeout=10)
                st.session_state.lista_local = cargar_datos()
                st.rerun()

    # Botón de limpieza siempre visible al final de la tabla
    if st.session_state.lista_local:
        df_show = pd.DataFrame(st.session_state.lista_local)[["Nombre", "ID", "Entidad", "mCI", "Estado"]]
        st.dataframe(df_show, use_container_width=True)
        
        st.divider()
        if st.button("🚨 LIMPIAR PANTALLA (RESETEAR SEMANA)", type="secondary", use_container_width=True):
            try:
                requests.post(SCRIPT_URL, timeout=10)
                st.session_state.lista_local = []
                st.success("Semana reiniciada.")
                st.rerun()
            except:
                st.error("Error al conectar con el servidor.")

# --- TAB 2: INVENTARIO (Lógica de Trazabilidad corregida) ---
with tab2:
    c1, c2 = st.columns([2, 1])
    c1.header("Control de Inventario")
    if st.session_state.lista_local:
        pdf = generar_pdf(st.session_state.lista_local)
        c2.download_button("📄 GENERAR REPORTE SEMANAL", data=pdf, file_name="reporte_nuclear.pdf", use_container_width=True)

        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                col_a, col_b = st.columns(2)
                
                n_est = col_a.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"], 
                                      index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"].index(p.get('Estado', 'PENDIENTE')), key=f"s_{idx}")
                
                # Aquí cargamos las notas actuales (que pueden traer el historial del anterior)
                n_not = col_a.text_area("Notas / Trazabilidad", value=p.get('Notas', ""), key=f"t_{idx}")
                
                if col_a.button("💾 Guardar y Cerrar", key=f"g_{idx}"):
                    # Al guardar cambios normales (como APLICADO), enviamos n_not que ya contiene el historial
                    params = {
                        "action": "update", "old_id": p['ID'], "id": p['ID'], 
                        "nombre": p['Nombre'], "entidad": p['Entidad'], 
                        "estado": n_est, "mci": p['mCI'], "notas": n_not
                    }
                    requests.get(SCRIPT_URL, params=params, timeout=15)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                if p.get('Estado') == "CANCELADO":
                    col_b.warning("Reasignar Dosis")
                    rn = col_b.text_input("Nuevo Nombre", key=f"rn_{idx}").upper()
                    ri = col_b.text_input("Nueva ID", key=f"ri_{idx}")
                    re = col_b.text_input("Nueva Entidad", key=f"re_{idx}").upper()
                    
                    if col_b.button("🔄 Ejecutar Reasignación", key=f"br_{idx}"):
                        if rn and ri:
                            # Capturamos toda la información del paciente que cancela
                            motivo_cancel = p.get('Notas', 'Sin motivo especificado')
                            hist = (f"REASIGNADO. Original: {p['Nombre']} | ID: {p['ID']} | "
                                   f"Entidad: {p['Entidad']} | Motivo: {motivo_cancel}")
                            
                            params = {
                                "action": "update", "old_id": p['ID'], "id": ri, 
                                "nombre": rn, "entidad": re, "estado": "RECIBIDO", 
                                "mci": p['mCI'], "notas": hist
                            }
                            requests.get(SCRIPT_URL, params=params, timeout=15)
                            st.session_state.lista_local = cargar_datos()
                            st.rerun()

# --- TAB 3: CALCULADORA ---
with tab3:
    st.header("Calculadora Decaimiento")
    col1, col2 = st.columns(2)
    a_i = col1.number_input("mCi Iniciales", 0.0, value=50.0)
    f_c = col1.date_input("Fecha Calibración")
    h_c = col1.time_input("Hora Calibración")
    f_f = col2.date_input("Fecha Consulta")
    h_f = col2.time_input("Hora Consulta")
    dt_i = datetime.combine(f_c, h_c)
    dt_f = datetime.combine(f_f, h_f)
    diff = (dt_f - dt_i).total_seconds() / 3600
    if diff >= 0:
        a_f = a_i * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Resultado", f"{round(a_f, 2)} mCi")
    else: st.error("Revisar fechas")
