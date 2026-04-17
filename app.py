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
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')

# CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # ttl=0 obliga a Streamlit a traer datos frescos de la hoja
        df = conn.read(ttl="0s")
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except:
        pass
    # Si la hoja está vacía, devuelve la estructura base
    return pd.DataFrame(columns=["Nombre", "ID", "Entidad", "Fecha Cápsula", "mCI"])

if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# FUNCIÓN PDF
def generar_pdf(df, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    elementos.append(Paragraph("<b>PROGRAMACIÓN YODO RADIACTIVO</b>", estilos['Title']))
    elementos.append(Spacer(1, 20))
    
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for _, p in df.iterrows():
        data.append([str(p['Nombre']), str(p['ID']), str(p['Entidad']), str(p['Fecha Cápsula']), str(p['mCI'])])
    
    tabla = Table(data, colWidths=[150, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"TOTAL DOSIS: {total} mCi", estilos['Normal']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# INTERFAZ
st.title("☢️ Registro de Pacientes - Barranquilla")

with st.sidebar.form("registro", clear_on_submit=True):
    st.header("Nuevo Ingreso")
    n = st.text_input("Nombre Completo").upper()
    i = st.text_input("Cédula / ID")
    e = st.text_input("Entidad (EPS)")
    d = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    f = st.date_input("Fecha de Cápsula")
    
    if st.form_submit_button("Sincronizar con Drive"):
        if n and i:
            # Crear nueva fila
            nuevo = pd.DataFrame([{
                "Nombre": n, "ID": i, "Entidad": e, 
                "Fecha Cápsula": f.strftime("%d/%m/%Y"), "mCI": d
            }])
            # Actualizar memoria local
            st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo], ignore_index=True)
            try:
                # ENVIAR A GOOGLE SHEETS
                conn.update(data=st.session_state.df_pacientes)
                st.sidebar.success("¡Datos guardados en Drive!")
            except Exception as error:
                st.sidebar.warning(f"Guardado localmente. Error Drive: {error}")
            st.rerun()

# MÉTRICAS Y TABLA
total_dosis = pd.to_numeric(st.session_state.df_pacientes['mCI'], errors='coerce').sum()
st.metric("Total Semanal", f"{total_dosis} mCi", f"{round(150-total_dosis, 2)} restantes")

if not st.session_state.df_pacientes.empty:
    st.dataframe(st.session_state.df_pacientes, use_container_width=True)
    pdf = generar_pdf(st.session_state.df_pacientes, total_dosis)
    st.download_button("📥 Descargar Reporte PDF", pdf, "programacion.pdf", use_container_width=True)
else:
    st.info("No hay pacientes registrados hoy.")
