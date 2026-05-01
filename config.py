import os
import streamlit as st

def get_script_url():
    try:
        return st.secrets["apps_script_url"]
    except (KeyError, FileNotFoundError):
        st.error("⚠️ La variable apps_script_url no está configurada en Secrets.")
        return ""

SCRIPT_URL = get_script_url()
HL_YODO_DIAS = 8.02
LOGO_PATH = "logo.png"
TIMEZONE = "America/Bogota"
COLUMNAS_REQUERIDAS = ["Nombre","ID","Entidad","Fecha_Capsula","mCI","Estado","Fecha_Recepcion","Fecha_Administracion","Notas"]
ESTADOS_VALIDOS = ["PENDIENTE","RECIBIDO","ADMINISTRADA","CANCELADO","DECAIMIENTO"]
