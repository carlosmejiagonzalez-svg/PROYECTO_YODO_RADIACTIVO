import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# Conexión que busca los secretos en la nube
conn = st.connection("hoja_nuclear", type=GSheetsConnection)

URL_EXCEL = "https://docs.google.com/spreadsheets/d/1Z1ELJYm6xq6w8HmwlCY8Qu1iHoWvH77cYNSVhcuaz9Y/edit"

st.title("☢️ Registro Medicina Nuclear")

with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Sincronizar con Google Sheets")

if enviar and nombre and cedula:
    try:
        df_existente = conn.read(spreadsheet=URL_EXCEL)
        nuevo = pd.DataFrame([{"Nombre": nombre, "ID": str(cedula), "mCI": dosis}])
        df_actualizado = pd.concat([df_existente, nuevo], ignore_index=True)
        conn.update(spreadsheet=URL_EXCEL, data=df_actualizado)
        st.sidebar.success(f"✅ ¡Sincronizado!: {nombre}")
        st.balloons()
    except Exception as e:
        st.sidebar.error(f"❌ Error: {e}")

st.write("### Lista de Pacientes")
try:
    df_visualizacion = conn.read(spreadsheet=URL_EXCEL, ttl=0)
    st.dataframe(df_visualizacion, use_container_width=True)
except:
    st.info("Conectando con la base de datos...")
