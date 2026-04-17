import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# Creamos el diccionario de credenciales aquí mismo
# Esto evita el error de "Invalid TOML" en la web de Streamlit
creds = {
    "type": "service_account",
    "project_id": "app-medicina-nuclear",
    "private_key_id": "c4de8fdb3341822fd79fe12a88c3c6faf6178171",
    "private_key": st.secrets.get("PRIVATE_KEY_PLANA", "").replace('\\n', '\n'),
    "client_email": "robot-medicina@app-medicina-nuclear.iam.gserviceaccount.com",
    "client_id": "113833402702332306124",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robot-medicina%40app-medicina-nuclear.iam.gserviceaccount.com"
}

# Conexión
try:
    conn = st.connection("hoja_nuclear", type=GSheetsConnection, **creds)
    url = st.secrets["URL_HOJA"]
except Exception as e:
    st.error(f"Error de configuración: {e}")

st.title("☢️ Registro Medicina Nuclear")

# Formulario de entrada
with st.sidebar.form("registro"):
    nombre = st.text_input("Nombre").upper()
    cedula = st.text_input("Cédula")
    mci = st.number_input("mCI", step=0.1)
    boton = st.form_submit_button("Sincronizar")

if boton and nombre and cedula:
    df_ex = conn.read(spreadsheet=url)
    nuevo = pd.DataFrame([{"Nombre": nombre, "ID": str(cedula), "mCI": mci}])
    df_final = pd.concat([df_ex, nuevo], ignore_index=True)
    conn.update(spreadsheet=url, data=df_final)
    st.success("¡Datos guardados!")

# Mostrar tabla
try:
    df = conn.read(spreadsheet=url, ttl=0)
    st.dataframe(df, use_container_width=True)
except:
    st.info("Esperando conexión...")
