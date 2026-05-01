import streamlit as st
from ui.tabs import render_programacion, render_inventario, render_calculadora
from services.data_service import cargar_datos

st.set_page_config(
    page_title="Nuclear 2000 Ltda",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "lista_local" not in st.session_state:
    st.session_state.lista_local = cargar_datos()

import os
col_logo, col_titulo = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=90)
with col_titulo:
    st.title("☢️ Nuclear 2000 Ltda")
    st.caption("Sistema de Gestión de Yodo I-131")

st.divider()

t1, t2, t3 = st.tabs(["📋 Programación", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

with t1:
    render_programacion()

with t2:
    render_inventario()

with t3:
    render_calculadora()
