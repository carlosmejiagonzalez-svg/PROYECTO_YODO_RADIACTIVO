import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración de página
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# --- CONEXIÓN ---
# 'hoja_nuclear' debe coincidir exactamente con el nombre en los Secrets
conn = st.connection("hoja_nuclear", type=GSheetsConnection)

# URL de tu Excel (la misma que ya tienes)
URL_EXCEL = "https://docs.google.com/spreadsheets/d/1Z1ELJYm6xq6w8HmwlCY8Qu1iHoWvH77cYNSVhcuaz9Y/edit"

st.title("☢️ Registro Medicina Nuclear")

# --- FORMULARIO DE REGISTRO ---
with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Sincronizar con Google Sheets")

if enviar:
    if nombre and cedula:
        try:
            # 1. Leer datos actuales del Excel
            df_existente = conn.read(spreadsheet=URL_EXCEL)
            
            # 2. Crear el nuevo registro
            nuevo_registro = pd.DataFrame([{
                "Nombre": nombre, 
                "ID": str(cedula), 
                "mCI": dosis
            }])
            
            # 3. Concatenar (unir) lo viejo con lo nuevo
            df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
            
            # 4. Subir todo de nuevo al Excel
            conn.update(spreadsheet=URL_EXCEL, data=df_actualizado)
            
            st.sidebar.success(f"✅ ¡Sincronizado!: {nombre}")
            st.balloons()
            st.cache_data.clear() # Limpiar memoria para ver el cambio
        except Exception as e:
            st.sidebar.error(f"❌ Error al sincronizar: {e}")
    else:
        st.sidebar.warning("⚠️ Por favor llena Nombre y Cédula")

# --- VISUALIZACIÓN DE DATOS ---
st.write("### Lista de Pacientes en tiempo real")
try:
    # Leer sin usar caché para ver los cambios de inmediato (ttl=0)
    df_visualizacion = conn.read(spreadsheet=URL_EXCEL, ttl=0)
    st.dataframe(df_visualizacion, use_container_width=True)
except Exception as e:
    st.info("Conectando con la base de datos de Google...")

# Botón para forzar recarga
if st.button("🔄 Actualizar Tabla"):
    st.cache_data.clear()
    st.rerun()
