import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de la página
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# 2. Función para limpiar y conectar
def conectar_bd():
    try:
        # Extraemos los datos de los Secrets
        conf = st.secrets["connections"]["gsheets"]
        
        # LIMPIEZA DE LLAVE: Esto arregla el error "Unable to load PEM file"
        # Asegura que los saltos de línea sean los correctos para Google
        raw_key = conf["private_key"]
        if "\\n" in raw_key:
            clean_key = raw_key.replace("\\n", "\n")
        else:
            clean_key = raw_key
            
        # Creamos un diccionario de credenciales limpio
        creds = {
            "type": conf["type"],
            "project_id": conf["project_id"],
            "private_key_id": conf["private_key_id"],
            "private_key": clean_key,
            "client_email": conf["client_email"],
            "client_id": conf["client_id"],
            "auth_uri": conf["auth_uri"],
            "token_uri": conf["token_uri"],
            "auth_provider_x509_cert_url": conf["auth_provider_x509_cert_url"],
            "client_x509_cert_url": conf["client_x509_cert_url"]
        }
        
        # Retornamos la conexión y la URL
        return st.connection("gsheets", type=GSheetsConnection, **creds), conf["spreadsheet"]
    except Exception as e:
        st.error(f"Error de configuración: {e}")
        return None, None

conn, url_hoja = conectar_bd()

st.title("☢️ Registro Medicina Nuclear")

# 3. Formulario de entrada
with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Sincronizar con Google Sheets")

# 4. Lógica de guardado
if enviar and conn:
    if nombre and cedula:
        try:
            df_existente = conn.read(spreadsheet=url_hoja)
            nuevo_registro = pd.DataFrame([{"Nombre": nombre, "ID": str(cedula), "mCI": dosis}])
            df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
            conn.update(spreadsheet=url_hoja, data=df_actualizado)
            
            st.sidebar.success(f"✅ Sincronizado: {nombre}")
            st.balloons()
            st.cache_data.clear()
        except Exception as e:
            st.sidebar.error(f"❌ Error al guardar: {e}")
    else:
        st.sidebar.warning("⚠️ Completa Nombre y Cédula.")

# 5. Tabla en tiempo real
st.write("### Lista de Pacientes")
if conn:
    try:
        df_visualizacion = conn.read(spreadsheet=url_hoja, ttl=0)
        st.dataframe(df_visualizacion, use_container_width=True)
    except:
        st.info("Conectando con la base de datos de Google...")

if st.button("🔄 Recargar Tabla"):
    st.cache_data.clear()
    st.rerun()
