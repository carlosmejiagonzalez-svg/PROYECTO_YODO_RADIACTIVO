import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from streamlit_gsheets import GSheetsConnection

# CONFIGURACIÓN
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
RUTA_LOGO = "logo.png"

# CONEXIÓN PÚBLICA (Solo usa la URL de Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # ttl=0 para que siempre traiga datos frescos del Excel
        df = conn.read(ttl="0s")
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception as e:
        st.error(f"Esperando conexión con Google Sheets...")
    return pd.DataFrame(columns=["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCI"])

if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# FUNCIÓN PDF
def generar_pdf_stream(df, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    
    if os.path.exists(RUTA_LOGO):
        try:
            img = Image(RUTA_LOGO, width=100, height=50)
            img.hAlign = 'LEFT'
            elementos.append(img)
        except: pass
    
    elementos.append(Paragraph("<b>PROGRAMACIÓN YODO RADIACTIVO</b>", estilos['Title']))
    elementos.append(Spacer(1, 12))
    
    # Datos para tabla
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for _, p in df.iterrows():
        data.append([str(p['Nombre']), str(p['ID']), str(p['Entidad']), str(p['Fecha Cápsula']), str(p['mCI'])])
    
    t = Table(data)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.grey), ('GRID',(0,0),(-1,-1),0.5,colors.black)]))
    elementos.append(t)
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(f"TOTAL: {total} mCi", estilos['Normal']))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# INTERFAZ
st.title("☢️ Registro Medicina Nuclear")

with st.sidebar.form("registro"):
    n = st.text_input("Nombre Completo").upper()
    i = st.text_input("ID / Cédula")
    e = st.text_input("Entidad")
    d = st.number_input("Dosis (mCi)", 0.0)
    f = st.date_input("Fecha")
    if st.form_submit_button("Sincronizar Datos"):
        if n and i:
            nuevo = pd.DataFrame([{"Nombre":n, "ID":i, "Entidad":e, "Fecha Cápsula":f.strftime("%d/%m/%Y"), "mCI":d}])
            st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo], ignore_index=True)
            try:
                conn.update(data=st.session_state.df_pacientes)
                st.success("Sincronizado!")
            except:
                st.warning("Guardado local (Error de conexión)")
            st.rerun()

# MOSTRAR DATOS
total = st.session_state.df_pacientes['mCI'].sum()
st.metric("Total Dosis", f"{total} mCi")
st.table(st.session_state.df_pacientes)

if not st.session_state.df_pacientes.empty:
    pdf = generar_pdf_stream(st.session_state.df_pacientes, total)
    st.download_button("Descargar PDF", pdf, "reporte.pdf")
