import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de la página
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# 2. Conexión simplificada
# Esta forma busca automáticamente la sección [connections.gsheets] en tus secretos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.info("Asegúrate de que los Secrets en Streamlit sigan el formato correcto.")

st.title("☢️ Registro Medicina Nuclear")

# 3. Formulario de entrada en la barra lateral
with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Sincronizar con Google Sheets")

# 4. Lógica de guardado
if enviar:
    if nombre and cedula:
        try:
            # Leer datos actuales
            df_existente = conn.read(spreadsheet=url_hoja)
            
            # Crear nuevo registro
            nuevo_registro = pd.DataFrame([{
                "Nombre": nombre, 
                "ID": str(cedula), 
                "mCI": dosis
            }])
            
            # Unir y actualizar
            df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
            conn.update(spreadsheet=url_hoja, data=df_actualizado)
            
            st.sidebar.success(f"✅ ¡Sincronizado!: {nombre}")
            st.balloons()
            st.cache_data.clear()
        except Exception as e:
            st.sidebar.error(f"❌ Error al sincronizar: {e}")
    else:
        st.sidebar.warning("⚠️ Por favor completa Nombre y Cédula")

# 5. Visualización de la tabla
st.write("### Lista de Pacientes en tiempo real")
try:
    df_visualizacion = conn.read(spreadsheet=url_hoja, ttl=0)
    st.dataframe(df_visualizacion, use_container_width=True)
except Exception as e:
    st.info("Esperando datos de la hoja de cálculo...")

# Botón manual de actualización
if st.button("🔄 Forzar Recarga de Tabla"):
    st.cache_data.clear()
    st.rerun()
