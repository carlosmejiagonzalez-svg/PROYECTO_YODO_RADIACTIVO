import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from streamlit_gsheets import GSheetsConnection

# CONFIGURACIÓN
st.set_page_config(page_title="Gestión Medicina Nuclear - SMQA", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')

# CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # Forzamos lectura fresca ignorando el caché
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except:
        pass
    return pd.DataFrame(columns=["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI"])

if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# FUNCIÓN PDF
def generar_pdf(df, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES - YODO 131</b>", estilos['Title']))
    elementos.append(Spacer(1, 20))
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for _, p in df.iterrows():
        data.append([str(p.get('Nombre','')), str(p.get('ID','')), str(p.get('Entidad','')), str(p.get('Fecha_Capsula','')), str(p.get('mCI','0'))])
    tabla = Table(data, colWidths=[160, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.darkblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
    elementos.append(tabla)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# INTERFAZ
st.title("☢️ Control de Medicina Nuclear - Atlántico")

with st.sidebar.form("registro", clear_on_submit=True):
    st.header("Registrar Paciente")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("Cédula / ID")
    entidad = st.text_input("Entidad").upper()
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    fecha = st.date_input("Fecha de Cápsula", value=datetime.now(colombia_tz))
    
    if st.form_submit_button("Sincronizar con Google Sheets"):
        if nombre and cedula:
            # 1. Crear el nuevo registro
            nuevo = pd.DataFrame([{
                "Nombre": nombre, "ID": cedula, "Entidad": entidad, 
                "Fecha_Capsula": fecha.strftime("%d/%m/%Y"), "mCI": dosis
            }])
            
            # 2. Actualizar la lista local
            st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo], ignore_index=True)
            
            try:
                # 3. INTENTO DE ESCRITURA FORZADA
                conn.update(data=st.session_state.df_pacientes)
                st.sidebar.success("✅ ¡Sincronizado!")
                st.cache_data.clear() # Limpiar memoria de Streamlit
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
            st.rerun()

# MOSTRAR
df_v = st.session_state.df_pacientes.copy()
df_v['mCI'] = pd.to_numeric(df_v['mCI'], errors='coerce').fillna(0)
total = df_v['mCI'].sum()

st.metric("Total Dosis", f"{total} mCi")
st.dataframe(df_v, use_container_width=True, hide_index=True)

if not df_v.empty:
    pdf = generar_pdf(df_v, total)
    st.download_button("📥 Descargar Reporte PDF", pdf, "programacion.pdf", use_container_width=True)

if st.button("🗑️ Resetear lista (Solo local)"):
    st.session_state.df_pacientes = pd.DataFrame(columns=["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI"])
    st.rerun()
