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

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Gestión Medicina Nuclear - SMQA", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')

# 2. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # ttl=0 asegura que traiga datos frescos
        df = conn.read(ttl="0s")
        if df is not None and not df.empty:
            # Limpiar nombres de columnas y asegurar que coincidan
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except:
        pass
    # Estructura base sin espacios en los nombres técnicos
    return pd.DataFrame(columns=["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI"])

# Inicializar sesión
if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# 3. FUNCIÓN REPORTE PDF
def generar_pdf(df, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES - YODO 131</b>", estilos['Title']))
    elementos.append(Paragraph("Sociedad Médico Quirúrgica del Atlántico", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for _, p in df.iterrows():
        data.append([
            str(p.get('Nombre', '')), 
            str(p.get('ID', '')), 
            str(p.get('Entidad', '')), 
            str(p.get('Fecha_Capsula', '')), 
            str(p.get('mCI', '0'))
        ])
    
    tabla = Table(data, colWidths=[160, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# 4. INTERFAZ
st.title("☢️ Control de Medicina Nuclear - Atlántico")

with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.header("Registrar Paciente")
    nombre_in = st.text_input("Nombre Completo").upper()
    cedula_in = st.text_input("Cédula / ID")
    entidad_in = st.text_input("Entidad (EPS)").upper()
    dosis_in = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    fecha_in = st.date_input("Fecha de Cápsula", value=datetime.now(colombia_tz))
    
    if st.form_submit_button("Sincronizar con Google Sheets"):
        if nombre_in and cedula_in:
            nuevo_paciente = pd.DataFrame([{
                "Nombre": nombre_in, 
                "ID": cedula_in, 
                "Entidad": entidad_in, 
                "Fecha_Capsula": fecha_in.strftime("%d/%m/%Y"), 
                "mCI": dosis_in
            }])
            
            st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo_paciente], ignore_index=True)
            
            try:
                # Sincronizar
                conn.update(data=st.session_state.df_pacientes)
                st.sidebar.success("✅ ¡Sincronizado!")
                st.cache_data.clear()
            except Exception as e:
                st.sidebar.error(f"⚠️ Error: {e}")
            
            st.rerun()

# 5. VISUALIZACIÓN
df_display = st.session_state.df_pacientes.copy()
df_display['mCI'] = pd.to_numeric(df_display['mCI'], errors='coerce').fillna(0)
total_acumulado = df_display['mCI'].sum()

st.metric("Total Dosis Programada", f"{total_acumulado} mCi")

if not df_display.empty:
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    pdf_reporte = generar_pdf(df_display, total_acumulado)
    st.download_button("📥 Descargar Reporte PDF", pdf_reporte, "programacion.pdf", use_container_width=True)
    
    if st.button("🗑️ Borrar lista local"):
        st.session_state.df_pacientes = pd.DataFrame(columns=["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI"])
        st.rerun()
else:
    st.info("No hay pacientes registrados.")
