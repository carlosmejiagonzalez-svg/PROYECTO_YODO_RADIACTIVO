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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Programación Yodo", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
RUTA_LOGO = "logo.png"

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # Intentamos leer la primera hoja disponible
        df = conn.read(ttl="0s")
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except:
        pass
    return pd.DataFrame(columns=["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCI"])

if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# --- FUNCIÓN PDF ---
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
    
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES YODO RADIACTIVO</b>", estilos['Title']))
    elementos.append(Spacer(1, 20))

    data = [["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha", "mCI"]]
    for _, p in df.iterrows():
        data.append([str(p.get(c, '')) for c in ["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCI"]])
    
    t = Table(data, colWidths=[110, 50, 60, 70, 30, 100, 70, 40])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.darkblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('FONTSIZE',(0,0),(-1,-1),7),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
    elementos.append(t)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"TOTAL: {total} mCi", estilos['Normal']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# --- INTERFAZ ---
st.title("☢️ Registro de Medicina Nuclear")

with st.sidebar.form("form_paciente", clear_on_submit=True):
    nombre = st.text_input("Nombre").upper()
    cedula = st.text_input("ID")
    tel = st.text_input("Teléfono")
    entidad = st.text_input("Entidad").upper()
    edad = st.number_input("Edad", 0, 120)
    diag = st.text_area("Diagnóstico").upper()
    fecha = st.date_input("Fecha", value=datetime.now(colombia_tz))
    dosis = st.number_input("mCi", 0.0, step=0.1)
    submit = st.form_submit_button("Añadir y Sincronizar")

if submit:
    if nombre and cedula:
        nuevo = pd.DataFrame([{"Nombre": nombre, "ID": cedula, "Teléfono": tel, "Entidad": entidad, "Edad": edad, "Diagnóstico": diag, "Fecha Cápsula": fecha.strftime("%d/%m/%Y"), "mCI": dosis}])
        st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo], ignore_index=True)
        
        try:
            # MÉTODO DEFINITIVO: Actualizamos sin especificar nombre de hoja para que use la principal (gid=0)
            conn.update(data=st.session_state.df_pacientes)
            st.sidebar.success(f"✅ Sincronizado en Excel")
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
        st.rerun()

# --- TABLA ---
total_mci = pd.to_numeric(st.session_state.df_pacientes['mCI'], errors='coerce').sum()
st.metric("Total Programado", f"{round(total_mci, 2)} mCi")

if not st.session_state.df_pacientes.empty:
    st.table(st.session_state.df_pacientes[["Nombre", "ID", "mCI"]])
    pdf = generar_pdf_stream(st.session_state.df_pacientes, round(total_mci, 2))
    st.download_button("📥 Descargar PDF", pdf, "programacion.pdf", use_container_width=True)