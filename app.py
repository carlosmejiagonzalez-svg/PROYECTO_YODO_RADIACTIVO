import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
from streamlit_gsheets import GSheetsConnection

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

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

st.title("☢️ Gestión Nuclear - Nuclear 2000 Ltda")
t1, t2, t3 = st.tabs(["📋 Pedidos", "📦 Inventario", "🧮 Calculadora"])

with t1:
    with st.sidebar.form("f1"):
        n = st.text_input("Nombre").upper()
        i = st.text_input("Cédula")
        e = st.text_input("Entidad").upper()
        d = st.number_input("mCi", 0.0)
        f = st.date_input("Fecha").strftime("%d/%m/%Y")
        if st.form_submit_button("Sincronizar"):
            requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
            st.session_state.lista_local = cargar_datos()
            st.rerun()
    if st.session_state.lista_local:
        st.dataframe(pd.DataFrame(st.session_state.lista_local)[["Nombre", "ID", "Entidad", "mCI", "Estado"]], use_container_width=True)

with t2:
    if st.session_state.lista_local:
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | ID: {p['ID']} | {p['Estado']}"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"], 
                                 index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"].index(p.get('Estado', 'PENDIENTE')), key=f"e{idx}")
                not_val = str(p.get('Notas', '')) if str(p.get('Notas', '')).lower() != 'nan' else ""
                notas = c1.text_area("Notas", value=not_val, key=f"n{idx}")
                
                if c1.button("💾 Guardar", key=f"b{idx}"):
                    params = {
                        "action": "update", "old_id": str(p['ID']).strip(), 
                        "id": str(p['ID']).strip(), "nombre": p['Nombre'], 
                        "entidad": p['Entidad'], "estado": est, 
                        "mci": p['mCI'], "notas": notas
                    }
                    requests.get(SCRIPT_URL, params=params)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                if p.get('Estado') == "CANCELADO":
                    rn = c2.text_input("Nuevo Nombre", key=f"rn{idx}").upper()
                    ri = c2.text_input("Nueva ID", key=f"ri{idx}")
                    if c2.button("🔄 Reasignar", key=f"rb{idx}"):
                        hist = f"Original: {p['Nombre']} | ID: {p['ID']} | Motivo: {notas}"
                        requests.get(SCRIPT_URL, params={"action":"update","old_id":str(p['ID']).strip(),"id":str(ri).strip(),"nombre":rn,"entidad":p['Entidad'],"estado":"RECIBIDO","mci":p['mCI'],"notas":hist})
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()
