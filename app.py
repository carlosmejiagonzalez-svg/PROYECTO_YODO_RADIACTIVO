import streamlit as st
import pandas as pd

# 1. Configuración básica
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")
st.title("☢️ Registro Medicina Nuclear")

# 2. URL de tu hoja (Asegúrate de que termine en /export?format=csv o similar)
# Esta es la forma más estable de conectar sin errores de credenciales
URL_SHEET = "https://docs.google.com/spreadsheets/d/1Z1ELJYm6xq6w8HmwlCY8Qu1iHoWvH77cYNSVhcuaz9Y/gviz/tq?tqx=out:csv"

# 3. Formulario Lateral
with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Guardar Registro")

# 4. Mostrar Datos
try:
    df = pd.read_csv(URL_SHEET)
    st.write("### Lista de Pacientes")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error("No se pudo cargar la base de datos. Verifica que la hoja sea pública.")

if enviar:
    st.info("Para escribir datos en la hoja sin llaves, te recomiendo usar un Google Form vinculado a esta hoja o simplificar los Secrets.")
