import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
from streamlit_gsheets import GSheetsConnection

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
            # Aseguramos que la ID se lea como TEXTO puro desde el inicio
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            columnas = ["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI", "Estado", "Fecha_Recepcion", "mCI_Real", "Notas"]
            for c in columnas:
                if c not in df.columns: df[c] = ""
            return df.to_dict('records')
    except Exception as e:
        st.error(f"Error cargando: {e}")
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

st.title("☢️ Control de Dosis - Nuclear 2000 Ltda")
tab1, tab2, tab3 = st.tabs(["📋 Programación", "📦 Inventario", "🧮 Calculadora"])

with tab1:
    with st.sidebar.form("reg_form"):
        st.header("Nuevo Pedido")
        n = st.text_input("Nombre").upper()
        i = st.text_input("ID / Cédula")
        e = st.text_input("Entidad").upper()
        d = st.number_input("mCi", 0.0)
        f = st.date_input("Fecha").strftime("%d/%m/%Y")
        if st.form_submit_button("Sincronizar"):
            if n and i:
                params = {"action": "register", "nombre": n, "id": str(i).strip(), "entidad": e, "mci": d, "fecha": f}
                requests.get(SCRIPT_URL, params=params, timeout=10)
                st.session_state.lista_local = cargar_datos()
                st.rerun()

    if st.session_state.lista_local:
        df_p = pd.DataFrame(st.session_state.lista_local)[["Nombre", "ID", "Entidad", "mCI", "Estado"]]
        st.dataframe(df_p, use_container_width=True)
        if st.button("🚨 REINICIAR"):
            requests.post(SCRIPT_URL)
            st.session_state.lista_local = []
            st.rerun()

with tab2:
    if st.session_state.lista_local:
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | ID: {p['ID']} | {p['Estado']}"):
                c1, c2 = st.columns(2)
                
                nuevo_est = c1.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"], 
                                         index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"].index(p.get('Estado', 'PENDIENTE')), 
                                         key=f"e_{idx}")
                
                current_not = str(p.get('Notas', ''))
                if current_not.lower() == 'nan': current_not = ""
                nueva_not = c1.text_area("Notas", value=current_not, key=f"n_{idx}")
                
                if c1.button("💾 Actualizar", key=f"b_{idx}"):
                    # Enviamos el ID exactamente como se cargó
                    p_id = str(p['ID']).strip()
                    params = {
                        "action": "update", "old_id": p_id, 
                        "id": p_id, "nombre": p['Nombre'], 
                        "entidad": p['Entidad'], "estado": nuevo_est, 
                        "mci": p['mCI'], "notes": nueva_not # Corregido a 'notas' en script, verificar consistencia
                        "notas": nueva_not
                    }
                    requests.get(SCRIPT_URL, params=params, timeout=15)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                if p.get('Estado') == "CANCELADO":
                    c2.info("Reasignar")
                    rn = c2.text_input("Nuevo Nombre", key=f"rn_{idx}").upper()
                    ri = c2.text_input("Nueva ID", key=f"ri_{idx}")
                    if c2.button("🔄 Ejecutar", key=f"rb_{idx}"):
                        hist = f"Original: {p['Nombre']} | ID: {p['ID']} | Motivo: {nueva_not}"
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
    # ... (Calculadora)
