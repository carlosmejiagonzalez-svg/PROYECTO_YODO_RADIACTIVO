import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')

# --- CONEXIÓN FORZADA (Nombre nuevo para evitar caché) ---
conn = st.connection("hoja_nuclear", type=GSheetsConnection)

def cargar_datos():
    try:
        # Forzamos lectura total
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except:
        pass
    return pd.DataFrame(columns=["Nombre", "ID", "mCI"])

if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

st.title("☢️ Registro de Pacientes")

# --- FORMULARIO ---
with st.sidebar.form("registro_nuclear", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Sincronizar con Google Sheets")

if enviar:
    if nombre and cedula:
        # Crear DataFrame con el nuevo paciente
        nuevo_p = pd.DataFrame([{
            "Nombre": nombre, 
            "ID": str(cedula), 
            "mCI": dosis
        }])
        
        # Unir al estado actual
        st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo_p], ignore_index=True)
        
        try:
            # Intentar actualización
            conn.update(data=st.session_state.df_pacientes)
            st.sidebar.success(f"✅ ¡Sincronizado!: {nombre}")
            st.cache_data.clear()
        except Exception as e:
            st.sidebar.error(f"Fallo de conexión: {e}")
        
        st.rerun()

# --- TABLA DE DATOS ---
st.write("### Datos en la Hoja de Cálculo")
if not st.session_state.df_pacientes.empty:
    st.dataframe(st.session_state.df_pacientes, use_container_width=True)
else:
    st.info("No hay pacientes registrados aún.")

# Botón para limpiar la vista local si es necesario
if st.button("Limpiar Vista Local"):
    st.session_state.df_pacientes = pd.DataFrame(columns=["Nombre", "ID", "mCI"])
    st.rerun()