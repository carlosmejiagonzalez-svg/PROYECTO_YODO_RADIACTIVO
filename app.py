import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Prueba de Conexión", layout="wide")

# --- CONEXIÓN ---
# No necesitas pasarle la URL aquí si ya está en los Secrets (Misterios)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN DE CARGA ---
def cargar_datos():
    try:
        # ttl=0 obliga a leer los datos reales de Google cada vez
        return conn.read(ttl=0)
    except:
        # Si la hoja está totalmente vacía, crea las columnas base
        return pd.DataFrame(columns=["Nombre", "ID", "mCI"])

# Inicializar la lista en la memoria de la web
if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

st.title("☢️ Prueba de Registro")

# --- FORMULARIO EN BARRA LATERAL ---
with st.sidebar.form("form_test"):
    nombre = st.text_input("Nombre").upper()
    cedula = st.text_input("ID")
    dosis = st.number_input("mCi", 0.0)
    boton = st.form_submit_button("Sincronizar ahora")

if boton:
    if nombre and cedula:
        # 1. Crear el nuevo registro
        nuevo = pd.DataFrame([{"Nombre": nombre, "ID": cedula, "mCI": dosis}])
        
        # 2. Unirlo a lo que ya existe
        st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo], ignore_index=True)
        
        try:
            # 3. ENVIAR A GOOGLE (Sin especificar hoja, para que use la principal)
            conn.update(data=st.session_state.df_pacientes)
            
            st.sidebar.success(f"✅ ¡Dato enviado!")
            # Limpiar la memoria interna de Streamlit para que "vea" el cambio
            st.cache_data.clear()
        except Exception as e:
            st.sidebar.error(f"❌ Fallo técnico: {e}")
        
        st.rerun()

# --- MOSTRAR TABLA ---
st.write("### Datos detectados en el Excel:")
st.table(st.session_state.df_pacientes)