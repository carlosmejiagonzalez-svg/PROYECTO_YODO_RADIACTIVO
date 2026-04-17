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

# Configuración de la página
st.set_page_config(page_title="Gestión Medicina Nuclear - SMQA", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')

# Estado de la sesión para mostrar los datos registrados en la pantalla actual
if 'lista_local' not in st.session_state:
    st.session_state.lista_local = []

# Función para generar el PDF con ReportLab
def generar_pdf(lista, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES - YODO 131</b>", estilos['Title']))
    elementos.append(Paragraph("Sociedad Médico Quirúrgica del Atlántico", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    # Encabezados de la tabla
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for p in lista:
        data.append([p['Nombre'], p['ID'], p['Entidad'], p['Fecha'], p['mCI']])
        
    tabla = Table(data, colWidths=[160, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),9),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# Interfaz Principal
st.title("☢️ Control de Medicina Nuclear - Atlántico")

with st.sidebar.form("registro", clear_on_submit=True):
    st.header("Registrar Paciente")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("Cédula / ID")
    entidad = st.text_input("Entidad (EPS)").upper()
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    fecha = st.date_input("Fecha de Cápsula", value=datetime.now(colombia_tz))
    
    if st.form_submit_button("Sincronizar con Google Sheets"):
        if nombre and cedula:
            fecha_str = fecha.strftime("%d/%m/%Y")
            
            # Parámetros para el Apps Script
            params = {
                "nombre": nombre,
                "id": cedula,
                "entidad": entidad,
                "fecha": fecha_str,
                "mci": dosis
            }
            
            try:
                # Envío de la petición GET al script de Google
                response = requests.get(SCRIPT_URL, params=params)
                
                if response.status_code == 200:
                    st.sidebar.success("✅ ¡Sincronizado en Google Drive!")
                    # Actualizar la lista que se ve en la app
                    nuevo = {
                        "Nombre": nombre, "ID": cedula, "Entidad": entidad, 
                        "Fecha": fecha_str, "mCI": dosis
                    }
                    st.session_state.lista_local.append(nuevo)
                else:
                    st.sidebar.error("Error: El servidor de Google respondió con error.")
            except Exception as e:
                st.sidebar.error(f"Error de conexión: {e}")
            
            st.rerun()

# Mostrar la tabla de resultados y opciones de descarga
if st.session_state.lista_local:
    df = pd.DataFrame(st.session_state.lista_local)
    total_mci = df['mCI'].sum()
    
    st.metric("Total Dosis Programada", f"{total_mci} mCi")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    pdf = generar_pdf(st.session_state.lista_local, total_mci)
    st.download_button(
        label="📥 Descargar Reporte PDF",
        data=pdf,
        file_name=f"programacion_smqa_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    if st.button("🗑️ Limpiar lista de la pantalla"):
        st.session_state.lista_local = []
        st.rerun()
else:
    st.info("No hay pacientes registrados en esta sesión. Ingrese datos en el panel izquierdo.")
