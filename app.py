import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de la página
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# 2. Preparación de credenciales y conexión
try:
    # URL guardada en los Secrets de Streamlit
    url_hoja = st.secrets["URL_HOJA"]
    
    # Diccionario de credenciales (usando la llave plana de los Secrets)
    creds_config = {
        "project_id": "app-medicina-nuclear",
        "private_key_id": "c4de8fdb3341822fd79fe12a88c3c6faf6178171",
        "private_key": st.secrets["PRIVATE_KEY_PLANA"].replace('\\n', '\n'),
        "client_email": "robot-medicina@app-medicina-nuclear.iam.gserviceaccount.com",
        "client_id": "113833402702332306124",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robot-medicina%40app-medicina-nuclear.iam.gserviceaccount.com"
    }

    # Creamos la conexión. 
    # Pasamos las credenciales desglosadas con ** para evitar duplicar el argumento 'type'
    conn = st.connection("hoja_nuclear", type=GSheetsConnection, **creds_config)
    
except Exception as e:
    st.error(f"Error en la configuración de credenciales: {e}")

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
    # ttl=0 para que siempre lea lo más nuevo
    df_visualizacion = conn.read(spreadsheet=url_hoja, ttl=0)
    st.dataframe(df_visualizacion, use_container_width=True)
except Exception as e:
    st.info("Esperando conexión con la base de datos...")

# Botón manual de actualización
if st.button("🔄 Forzar Recarga de Tabla"):
    st.cache_data.clear()
    st.rerun()
