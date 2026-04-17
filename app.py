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

# Inicializar la lista en el estado de la sesión
if 'lista_local' not in st.session_state:
    st.session_state.lista_local = []

# Función para generar el PDF
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
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

st.title("☢️ Control de Medicina Nuclear - Atlántico")

# Cálculo de dosis acumulada
dosis_actual = sum(float(p['mCI']) for p in st.session_state.lista_local)
restante = LIMITE_SEMANAL - dosis_actual

# --- FORMULARIO DE REGISTRO ---
with st.sidebar.form("registro", clear_on_submit=True):
    st.header("Registrar Paciente")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("Cédula / ID")
    entidad = st.text_input("Entidad (EPS)").upper()
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    fecha = st.date_input("Fecha de Cápsula", value=datetime.now(colombia_tz))
    
    if st.form_submit_button("Sincronizar con Drive"):
        if nombre and cedula:
            if (dosis_actual + dosis) > LIMITE_SEMANAL:
                st.sidebar.error(f"❌ ¡ALERTA! Supera el límite de {LIMITE_SEMANAL} mCi. Cupo: {restante} mCi")
            else:
                fecha_str = fecha.strftime("%d/%m/%Y")
                params = {"nombre": nombre, "id": cedula, "entidad": entidad, "fecha": fecha_str, "mci": dosis}
                try:
                    response = requests.get(SCRIPT_URL, params=params)
                    if response.status_code == 200:
                        st.sidebar.success("✅ Sincronizado")
                        nuevo = {"Nombre": nombre, "ID": cedula, "Entidad": entidad, "Fecha": fecha_str, "mCI": dosis}
                        st.session_state.lista_local.append(nuevo)
                    else:
                        st.sidebar.error("Error en servidor Google")
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
            st.rerun()

# --- MÉTRICAS ---
c1, c2 = st.columns(2)
c1.metric("Total Programado", f"{dosis_actual} mCi")
c2.metric("Cupo Disponible", f"{restante} mCi", delta_color="normal" if restante > 0 else "inverse")

if dosis_actual >= LIMITE_SEMANAL:
    st.warning("⚠️ Límite de 150 mCi alcanzado.")

st.divider()

# --- TABLA CON OPCIÓN DE ELIMINAR INDIVIDUAL ---
if st.session_state.lista_local:
    st.subheader("Pacientes en la sesión actual")
    
    # Crear encabezados de columnas para la tabla "manual"
    cols = st.columns([3, 2, 2, 2, 1, 1])
    cols[0].write("**Nombre**")
    cols[1].write("**ID**")
    cols[2].write("**Entidad**")
    cols[3].write("**Fecha**")
    cols[4].write("**mCI**")
    cols[5].write("**Acción**")

    # Iterar sobre la lista para crear las filas y los botones de borrar
    for index, paciente in enumerate(st.session_state.lista_local):
        row_cols = st.columns([3, 2, 2, 2, 1, 1])
        row_cols[0].write(paciente['Nombre'])
        row_cols[1].write(paciente['ID'])
        row_cols[2].write(paciente['Entidad'])
        row_cols[3].write(paciente['Fecha'])
        row_cols[4].write(paciente['mCI'])
        
        # Botón para eliminar (usa una llave única basada en el índice)
        if row_cols[5].button("🗑️", key=f"btn_{index}"):
            st.session_state.lista_local.pop(index)
            st.rerun()

    st.divider()
    
    # Botones de acción final
    pdf = generar_pdf(st.session_state.lista_local, dosis_actual)
    st.download_button("📥 Descargar Reporte PDF", pdf, "programacion.pdf", use_container_width=True)
    
    if st.button("🚨 Borrar TODA la lista de pantalla"):
        st.session_state.lista_local = []
        st.rerun()
else:
    st.info("No hay pacientes registrados en esta sesión.")
