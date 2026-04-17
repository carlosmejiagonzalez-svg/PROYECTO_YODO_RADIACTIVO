import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
import os
from streamlit_gsheets import GSheetsConnection

# URL de tu Script (Asegúrate de implementar la Nueva Versión en Apps Script)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda - Gestión Total", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df.to_dict('records')
    except: pass
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

st.title("☢️ Gestión de Medicina Nuclear - Nuclear 2000 Ltda")
tab1, tab2, tab3 = st.tabs(["📋 Programación", "📦 Inventario", "🧮 Calculadora"])

dosis_actual = sum(float(p.get('mCI', 0)) for p in st.session_state.lista_local)

# --- TAB 1: REGISTRO ---
with tab1:
    with st.sidebar.form("registro", clear_on_submit=True):
        st.header("Nuevo Pedido")
        nombre = st.text_input("Nombre").upper()
        cedula = st.text_input("ID")
        entidad = st.text_input("Entidad").upper()
        dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
        if st.form_submit_button("Sincronizar Pedido"):
            if nombre and cedula:
                params = {
                    "action": "register", "nombre": nombre, "id": cedula, 
                    "entidad": entidad, "mci": dosis, 
                    "fecha": datetime.now(colombia_tz).strftime("%d/%m/%Y")
                }
                requests.get(SCRIPT_URL, params=params, timeout=10)
                st.session_state.lista_local = cargar_datos()
                st.rerun()
    
    st.metric("Total Semanal", f"{round(dosis_actual, 2)} mCi")
    if st.session_state.lista_local:
        df_view = pd.DataFrame(st.session_state.lista_local)
        st.dataframe(df_view, use_container_width=True)
        if st.button("🚨 LIMPIAR SEMANA"):
            requests.post(SCRIPT_URL, timeout=10)
            st.session_state.lista_local = []
            st.rerun()

# --- TAB 2: INVENTARIO Y REASIGNACIÓN TOTAL ---
with tab2:
    st.header("Manejo de Escenarios")
    for idx, p in enumerate(st.session_state.lista_local):
        with st.expander(f"📍 {p['Nombre']} - {p['mCI']} mCi"):
            c1, c2 = st.columns(2)
            
            # Gestión Normal
            n_est = c1.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"], 
                               index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"].index(p.get('Estado', 'PENDIENTE')),
                               key=f"e_{idx}")
            n_not = c1.text_area("Notas", value=p.get('Notas', ""), key=f"n_{idx}")
            
            if c1.button("💾 Guardar Cambios", key=f"b_{idx}"):
                params = {
                    "action": "update", "old_id": p['ID'], "id": p['ID'], 
                    "nombre": p['Nombre'], "entidad": p['Entidad'], 
                    "estado": n_est, "mci": p['mCI'], "notas": n_not
                }
                try:
                    requests.get(SCRIPT_URL, params=params, timeout=15)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()
                except: st.rerun()

            # REASIGNACIÓN COMPLETA
            if p.get('Estado') == "CANCELADO":
                c2.warning("Reemplazar Paciente Anterior")
                rn = c2.text_input("Nombre Nuevo", key=f"rn_{idx}").upper()
                ri = c2.text_input("ID Nuevo", key=f"ri_{idx}")
                re = c2.text_input("Entidad Nueva", key=f"re_{idx}").upper()
                rd = c2.number_input("Dosis (mCi)", value=float(p['mCI']), key=f"rd_{idx}")
                
                if c2.button("🔄 Ejecutar Reasignación Total", key=f"br_{idx}"):
                    if rn and ri and re:
                        params = {
                            "action": "update", "old_id": p['ID'], "id": ri, 
                            "nombre": rn, "entidad": re, "estado": "RECIBIDO", 
                            "mci": rd, "notas": f"Reemplazó a {p['Nombre']}"
                        }
                        requests.get(SCRIPT_URL, params=params, timeout=15)
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()
                    else:
                        c2.error("Por favor llena todos los datos del nuevo paciente")

# --- TAB 3: CALCULADORA ---
with tab3:
    st.header("Cálculo de Decaimiento")
    c_cal1, c_cal2 = st.columns(2)
    a_ini = c_cal1.number_input("Actividad Inicial (mCi)", 0.0, value=50.0)
    f_cal = c_cal1.date_input("Fecha de calibración")
    h_cal = c_cal1.time_input("Hora de calibración")
    
    f_fut = c_cal2.date_input("Fecha a Consultar")
    h_fut = c_cal2.time_input("Hora a Consultar")
    
    dt_i = datetime.combine(f_cal, h_cal)
    dt_f = datetime.combine(f_fut, h_fut)
    diff = (dt_f - dt_i).total_seconds() / 3600
    
    if diff >= 0:
        a_fin = a_ini * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Actividad Resultante", f"{round(a_fin, 2)} mCi")
    else: st.error("La consulta debe ser posterior a la calibración")
