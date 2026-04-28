import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection

# URL de tu Apps Script
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda", layout="wide")

# Conexión principal
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_seguro(nombre_pestaña, indice):
    try:
        # Intento 1: Por nombre (más legible)
        df = conn.read(worksheet=nombre_pestaña, ttl=0)
        return df
    except:
        try:
            # Intento 2: Por índice (físico) si el nombre falla
            df = conn.read(worksheet=indice, ttl=0)
            return df
        except Exception as e:
            st.error(f"Error crítico: No se pudo acceder a la hoja {nombre_pestaña}. Revisa si la pestaña existe en el Excel.")
            return None

# --- ESTRUCTURA DE TABS ---
t1, t2, t3, t4 = st.tabs(["👥 Base de Datos", "📅 Programar Semana", "📦 Inventario", "🧮 Calculadora"])

with t1:
    st.subheader("📝 Registro de Pacientes en Espera")
    # Formulario de registro...
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        n = col1.text_input("Nombre Completo").upper()
        i = col1.text_input("Identificación")
        e = col2.text_input("Entidad").upper()
        d = col2.number_input("Dosis mCi", 0.0)
        f = st.date_input("Fecha Tentativa").strftime("%d/%m/%Y")
        if st.form_submit_button("Guardar en Base de Datos"):
            if n and i:
                requests.get(SCRIPT_URL, params={"action":"crear_maestro","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
                st.cache_data.clear()
                st.success("Registrado con éxito"); st.rerun()

    st.divider()
    # Cargamos la pestaña 2 (Base_Datos)
    df_base = cargar_datos_seguro("Base_Datos", 1)
    if df_base is not None and not df_base.empty:
        st.dataframe(df_base, use_container_width=True)

with t2:
    st.subheader("🚀 Pasar Paciente a la Lista Semanal")
    df_base = cargar_datos_seguro("Base_Datos", 1)
    if df_base is not None and not df_base.empty:
        # Limpieza de IDs para evitar el .0
        df_base['ID'] = df_base['ID'].astype(str).str.replace(r'\.0$', '', regex=True)
        opciones = df_base['Nombre'] + " (" + df_base['ID'] + ")"
        pac_sel = st.selectbox("Seleccionar paciente para activar", opciones)
        
        if st.button("Mover a Programación"):
            id_ext = pac_sel.split("(")[1].replace(")","").strip()
            requests.get(SCRIPT_URL, params={"action":"programar_desde_base", "id":id_ext})
            st.cache_data.clear(); st.rerun()
    
    st.divider()
    # Cargamos la pestaña 1 (Hoja 1)
    df_sem = cargar_datos_seguro("Hoja 1", 0)
    if df_sem is not None and not df_sem.empty:
        st.write("### Pacientes Programados")
        st.table(df_sem[['Nombre', 'ID', 'Entidad', 'mCI']])
