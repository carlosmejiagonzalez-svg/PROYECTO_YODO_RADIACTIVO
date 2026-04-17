import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
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
            columnas = ["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI", "Estado", "Fecha_Recepcion", "mCI_Real", "Notas"]
            for c in columnas:
                if c not in df.columns: df[c] = ""
            return df.to_dict('records')
    except: pass
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

st.title("☢️ Gestión Nuclear - Nuclear 2000 Ltda")
tab1, tab2, tab3 = st.tabs(["📋 Programación", "📦 Inventario", "🧮 Calculadora"])

with tab1:
    with st.sidebar.form("reg_form"):
        st.header("Nuevo Pedido")
        n = st.text_input("Nombre").upper()
        i = st.text_input("Cédula")
        e = st.text_input("Entidad").upper()
        d = st.number_input("mCi", 0.0)
        f = st.date_input("Fecha").strftime("%d/%m/%Y")
        if st.form_submit_button("Sincronizar Pedido"):
            if n and i:
                p = {"action": "register", "nombre": n, "id": i, "entidad": e, "mci": d, "fecha": f}
                requests.get(SCRIPT_URL, params=p, timeout=10)
                st.session_state.lista_local = cargar_datos()
                st.rerun()

    if st.session_state.lista_local:
        df_p = pd.DataFrame(st.session_state.lista_local)[["Nombre", "ID", "Entidad", "mCI", "Estado"]]
        st.dataframe(df_p, use_container_width=True)
        if st.button("🚨 LIMPIAR TODO"):
            requests.post(SCRIPT_URL)
            st.session_state.lista_local = []
            st.rerun()

with tab2:
    if st.session_state.lista_local:
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                col1, col2 = st.columns(2)
                
                nuevo_est = col1.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"], 
                                         index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"].index(p.get('Estado', 'PENDIENTE')), 
                                         key=f"est_{idx}")
                
                # Manejo de 'nan' para las notas
                current_notas = str(p.get('Notas', ''))
                if current_notas.lower() == 'nan': current_notas = ""
                
                nueva_not = col1.text_area("Notas / Trazabilidad", value=current_notas, key=f"not_{idx}")
                
                if col1.button("💾 Guardar Cambios", key=f"btn_{idx}"):
                    params = {
                        "action": "update", "old_id": str(p['ID']).strip(), 
                        "id": str(p['ID']).strip(), "nombre": p['Nombre'], 
                        "entidad": p['Entidad'], "estado": nuevo_est, 
                        "mci": p['mCI'], "notas": nueva_not
                    }
                    resp = requests.get(SCRIPT_URL, params=params, timeout=15)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                if p.get('Estado') == "CANCELADO":
                    col2.warning("Reasignación")
                    rn = col2.text_input("Nuevo Nombre", key=f"rn_{idx}").upper()
                    ri = col2.text_input("Nueva ID", key=f"ri_{idx}")
                    if col2.button("🔄 Ejecutar Reasignación", key=f"re_{idx}"):
                        hist = f"REASIGNADO. Original: {p['Nombre']} | Motivo: {nueva_not}"
                        params = {
                            "action": "update", "old_id": str(p['ID']).strip(), 
                            "id": str(ri).strip(), "nombre": rn, 
                            "entidad": p['Entidad'], "estado": "RECIBIDO", 
                            "mci": p['mCI'], "notas": hist
                        }
                        requests.get(SCRIPT_URL, params=params, timeout=15)
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()

with tab3:
    st.header("Calculadora")
    # ... (Calculadora estándar)
