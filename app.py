import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import json

# 1. Configuración de la página
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# 2. LIMPIADOR DE LLAVE (Fuerza Bruta)
def obtener_conexion():
    try:
        # Extraemos los datos de los secrets
        s = st.secrets["connections"]["gsheets"]
        
        # Limpiamos la llave privada de cualquier carácter extraño o mala codificación
        p_key = s["private_key"].replace("\\n", "\n")
        if not p_key.startswith("-----BEGIN PRIVATE KEY-----"):
            p_key = f"-----BEGIN PRIVATE KEY-----\n{p_key}"
        if not p_key.endswith("-----END PRIVATE KEY-----"):
            p_key = f"{p_key}\n-----END PRIVATE KEY-----"

        # Construimos el diccionario de credenciales manual
        creds = {
            "type": "service_account",
            "project_id": s["project_id"],
            "private_key_id": s["private_key_id"],
            "private_key": p_key,
            "client_email": s["client_email"],
            "client_id": s["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": s["client_x509_cert_url"]
        }
        
        return st.connection("gsheets", type=GSheetsConnection, **creds), s["spreadsheet"]
    except Exception as e:
        st.error(f"Error procesando credenciales: {e}")
        return None, None

conn, url_hoja = obtener_conexion()

st.title("☢️ Registro Medicina Nuclear")

# 3. Formulario (Barra lateral)
with st.sidebar.form("registro", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Sincronizar")

# 4. Lógica de Guardado
if enviar and conn:
    if nombre and cedula:
        try:
            df_actual = conn.read(spreadsheet=url_hoja)
            nuevo = pd.DataFrame([{"Nombre": nombre, "ID": str(cedula), "mCI": dosis}])
            df_final = pd.concat([df_actual, nuevo], ignore_index=True)
            conn.update(spreadsheet=url_hoja, data=df_final)
            st.sidebar.success("✅ ¡Guardado!")
            st.cache_data.clear()
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

# 5. Visualización
st.write("### Datos Actuales")
if conn:
    try:
        df_ver = conn.read(spreadsheet=url_hoja, ttl=0)
        st.dataframe(df_ver, use_container_width=True)
    except:
        st.info("Conectando...")
