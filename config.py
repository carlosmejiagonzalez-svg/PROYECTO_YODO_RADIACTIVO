import os
import streamlit as st

def get_secret(nombre):
    try:
        return str(st.secrets.get(nombre, "")).strip()
    except (KeyError, FileNotFoundError):
        return ""

SCRIPT_URL = get_secret("apps_script_url")
SCRIPT_TOKEN = get_secret("apps_script_token")
HL_YODO_DIAS = 8.02
LOGO_PATH = "logo.png"
TIMEZONE = "America/Bogota"
COLUMNAS_REQUERIDAS = ["Nombre","ID","Entidad","Fecha_Capsula","mCI","Estado","Fecha_Recepcion","Fecha_Administracion","Notas","ID_Tratamiento"]
ESTADOS_VALIDOS = ["PENDIENTE","RECIBIDO","ADMINISTRADA","CANCELADO","DECAIMIENTO"]

