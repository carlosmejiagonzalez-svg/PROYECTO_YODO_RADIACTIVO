import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# Conexión limpia
try:
    # Esta línea busca el bloque [connections.gsheets] en tus Secrets automáticamente
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Error de conexión: {e}")

st.title("☢️ Registro Medicina Nuclear")

# Formulario lateral
with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Sincronizar Datos")

# Lógica de guardado
if enviar:
    if nombre and cedula:
        try:
            df_existente = conn.read(spreadsheet=url_hoja)
            nuevo_registro = pd.DataFrame([{"Nombre": nombre, "ID": str(cedula), "mCI": dosis}])
            df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
            conn.update(spreadsheet=url_hoja, data=df_actualizado)
            st.sidebar.success(f"✅ Sincronizado: {nombre}")
            st.cache_data.clear()
            st.balloons()
        except Exception as e:
            st.sidebar.error(f"Error al guardar: {e}")
    else:
        st.sidebar.warning("⚠️ Completa Nombre y Cédula.")

# Tabla en tiempo real
st.write("### Lista de Pacientes")
try:
    df_visualizacion = conn.read(spreadsheet=url_hoja, ttl=0)
    st.dataframe(df_visualizacion, use_container_width=True)
except:
    st.info("Conectando con Google Sheets...")
