import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de la interfaz
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# 2. Conexión Estable
# Al no pasarle argumentos manuales aquí, evitamos el error de 'multiple values'
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Obtenemos la URL directamente de la sección de conexiones en secrets
    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Error de configuración inicial: {e}")

st.title("☢️ Registro Medicina Nuclear")

# 3. Formulario Lateral
with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.subheader("Nuevo Ingreso")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    enviar = st.form_submit_button("Sincronizar Datos")

# 4. Lógica de Guardado
if enviar:
    if nombre and cedula:
        try:
            # Leemos la base de datos actual
            df_existente = conn.read(spreadsheet=url_hoja)
            
            # Creamos el nuevo registro
            nuevo_registro = pd.DataFrame([{
                "Nombre": nombre, 
                "ID": str(cedula), 
                "mCI": dosis
            }])
            
            # Concatenamos y actualizamos la hoja
            df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
            conn.update(spreadsheet=url_hoja, data=df_actualizado)
            
            st.sidebar.success(f"✅ Sincronizado correctamente: {nombre}")
            st.balloons()
            st.cache_data.clear()
        except Exception as e:
            st.sidebar.error(f"❌ Error al sincronizar con Google Sheets: {e}")
    else:
        st.sidebar.warning("⚠️ El nombre y la cédula son campos obligatorios.")

# 5. Visualización de la Tabla
st.write("### Lista de Pacientes (Tiempo Real)")
try:
    # Usamos ttl=0 para que siempre traiga los datos más frescos
    df_visualizacion = conn.read(spreadsheet=url_hoja, ttl=0)
    st.dataframe(df_visualizacion, use_container_width=True)
except:
    st.info("Esperando conexión con la base de datos de Google...")

if st.button("🔄 Forzar Recarga"):
    st.cache_data.clear()
    st.rerun()
