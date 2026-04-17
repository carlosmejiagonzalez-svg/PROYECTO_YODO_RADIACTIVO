import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io

# URL de tu Google Apps Script
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Gestión Medicina Nuclear - SMQA", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')

# LÍMITE DE SEGURIDAD
LIMITE_SEMANAL = 150.0

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = []

def generar_pdf(lista, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES - YODO 131</b>", estilos['Title']))
    elementos.append(Paragraph("Sociedad Médico Quirúrgica del Atlántico", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for p in lista:
        data.append([p['Nombre'], p['ID'], p['Entidad'], p['Fecha'], p['mCI']])
    tabla = Table(data, colWidths=[160, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.darkblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

st.title("☢️ Control de Medicina Nuclear - Atlántico")

# Cálculo de dosis actual
df_temp = pd.DataFrame(st.session_state.lista_local)
dosis_actual = df_temp['mCI'].sum() if not df_temp.empty else 0.0
restante = LIMITE_SEMANAL - dosis_actual

with st.sidebar.form("registro", clear_on_submit=True):
    st.header("Registrar Paciente")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("Cédula / ID")
    entidad = st.text_input("Entidad (EPS)").upper()
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    fecha = st.date_input("Fecha de Cápsula", value=datetime.now(colombia_tz))
    
    if st.form_submit_button("Sincronizar con Drive"):
        if nombre and cedula:
            # VALIDACIÓN DE LÍMITE
            if (dosis_actual + dosis) > LIMITE_SEMANAL:
                st.sidebar.error(f"❌ ¡ALERTA! Esta dosis supera el límite de {LIMITE_SEMANAL} mCi. Solo quedan {restante} mCi disponibles.")
            else:
                fecha_str = fecha.strftime("%d/%m/%Y")
                params = {"nombre": nombre, "id": cedula, "entidad": entidad, "fecha": fecha_str, "mci": dosis}
                
                try:
                    response = requests.get(SCRIPT_URL, params=params)
                    if response.status_code == 200:
                        st.sidebar.success("✅ Sincronizado correctamente")
                        nuevo = {"Nombre": nombre, "ID": cedula, "Entidad": entidad, "Fecha": fecha_str, "mCI": dosis}
                        st.session_state.lista_local.append(nuevo)
                    else:
                        st.sidebar.error("Error en servidor de Google")
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
            st.rerun()

# INDICADORES VISUALES
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Dosis Programada", f"{dosis_actual} mCi")
with col2:
    color_restante = "normal" if restante > 10 else "inverse"
    st.metric("Cupo Disponible", f"{restante} mCi", delta_color=color_restante)

if dosis_actual >= LIMITE_SEMANAL:
    st.warning("⚠️ Se ha alcanzado o superado el límite de seguridad de 150 mCi para esta semana.")

if st.session_state.lista_local:
    st.dataframe(pd.DataFrame(st.session_state.lista_local), use_container_width=True, hide_index=True)
    pdf = generar_pdf(st.session_state.lista_local, dosis_actual)
    st.download_button("📥 Descargar Reporte PDF", pdf, "programacion.pdf", use_container_width=True)
    
    if st.button("🗑️ Limpiar lista de la pantalla"):
        st.session_state.lista_local = []
        st.rerun()
