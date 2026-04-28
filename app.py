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

SCRIPT_URL = "TU_NUEVA_URL_DE_APPS_SCRIPT"
LOGO_PATH = "logo.png" 

st.set_page_config(page_title="Nuclear 2000 Ltda", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(hoja=0):
    try:
        # hoja 0: Semanal, hoja 1: Base de Datos
        df = conn.read(worksheet=hoja, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            return df.to_dict('records')
    except: pass
    return []

# --- 4 PESTAÑAS ---
t1, t2, t3, t4 = st.tabs(["👥 Base de Datos", "📅 Programar Semana", "📦 Inventario", "🧮 Calculadora"])

# PESTAÑA 1: CREAR PACIENTES (Bandeja de Entrada)
with t1:
    st.subheader("Crear Paciente en Espera")
    with st.form("f_base", clear_on_submit=True):
        n, i, e = st.text_input("Nombre").upper(), st.text_input("Cédula"), st.text_input("Entidad").upper()
        d = st.number_input("Dosis sugerida mCi", 0.0)
        if st.form_submit_button("Guardar en Base de Datos"):
            requests.get(SCRIPT_URL, params={"action":"crear_maestro","nombre":n,"id":i,"entidad":e,"mci":d})
            st.success("Guardado en espera"); st.rerun()
    
    st.write("---")
    st.subheader("Pacientes en Espera")
    lista_base = cargar_datos(hoja=1)
    if lista_base:
        st.table(pd.DataFrame(lista_base)[["Nombre", "ID", "Entidad", "mCI"]])

# PESTAÑA 2: PROGRAMACIÓN SEMANAL (Donde se mueven y borran)
with t2:
    st.subheader("Pasar Paciente a Programación Real")
    lista_base = cargar_datos(hoja=1)
    if lista_base:
        df_b = pd.DataFrame(lista_base)
        paciente_sel = st.selectbox("Seleccionar Paciente de la Base", df_b['Nombre'] + " - " + df_b['ID'])
        id_sel = paciente_sel.split(" - ")[1]
        f_real = st.date_input("Fecha de Toma de Cápsula").strftime("%d/%m/%Y")
        
        if st.button("Programar para esta semana"):
            requests.get(SCRIPT_URL, params={"action":"programar_desde_base", "id":id_sel, "fecha":f_real})
            st.success("Movido a la lista de yodo"); st.rerun()

    st.divider()
    lista_semanal = cargar_datos(hoja=0)
    if lista_semanal:
        df_s = pd.DataFrame(lista_semanal)
        total = pd.to_numeric(df_s[~df_s['Estado'].isin(['CANCELADO'])]['mCI']).sum()
        st.metric("Total mCi Pedido", f"{total} mCi")
        st.dataframe(df_s)

# PESTAÑA 3: INVENTARIO (Tu lógica de RECIBIDO/ADMINISTRADO)
with t3:
    # Aquí pegas el código de los expanders que ya tienes funcionando
    st.info("Manejo de estados y trazabilidad")

# PESTAÑA 4: CALCULADORA (Restaurada)
with t4:
    st.header("🧮 Calculadora I-131")
    ai = st.number_input("Actividad Inicial (mCi)", value=100.0)
    fc, hc = st.date_input("Fecha Calibración"), st.time_input("Hora Calibración")
    ff, hf = st.date_input("Fecha Cálculo"), st.time_input("Hora Cálculo")
    dt1, dt2 = datetime.combine(fc, hc), datetime.combine(ff, hf)
    diff = (dt2 - dt1).total_seconds() / 3600
    if diff >= 0:
        af = ai * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Actividad Final", f"{round(af, 2)} mCi")
