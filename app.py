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
from streamlit_gsheets import GSheetsConnection

# URL de tu Google Apps Script
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Gestión Medicina Nuclear - SMQA", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')

# LÍMITE DE SEGURIDAD
LIMITE_SEMANAL = 150.0

# --- CONEXIÓN PARA LECTURA ---
# Usamos la conexión nativa para leer los datos que ya están en la hoja
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_desde_drive():
    try:
        # ttl=0 para que siempre traiga lo último de la hoja al recargar
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            # Limpiar nombres de columnas y convertir a lista de diccionarios
            df.columns = [str(c).strip() for c in df.columns]
            return df.to_dict('records')
    except Exception as e:
        st.error(f"Error al conectar con Drive para leer: {e}")
    return []

# INICIALIZACIÓN: Si la lista está vacía, intenta cargarla de Google Sheets
if 'lista_local' not in st.session_state or not st.session_state.lista_local:
    st.session_state.lista_local = cargar_datos_desde_drive()

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
        data.append([p.get('Nombre',''), p.get('ID',''), p.get('Entidad',''), p.get('Fecha_Capsula', p.get('Fecha','')), p.get('mCI', 0)])
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

# Cálculo de dosis acumulada (asegurando que mCI sea número)
dosis_actual = sum(float(p.get('mCI', 0)) for p in st.session_state.lista_local)
restante = LIMITE_SEMANAL - dosis_actual

# --- FORMULARIO EN BARRA LATERAL ---
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
                st.sidebar.error(f"❌ Supera el límite de {LIMITE_SEMANAL} mCi.")
            else:
                fecha_str = fecha.strftime("%d/%m/%Y")
                params = {"nombre": nombre, "id": cedula, "entidad": entidad, "fecha": fecha_str, "mci": dosis}
                try:
                    # Enviamos a través del Apps Script
                    response = requests.get(SCRIPT_URL, params=params)
                    if response.status_code == 200:
                        st.sidebar.success("✅ Sincronizado en Drive")
                        # Agregamos a la lista local para verlo de inmediato
                        nuevo = {"Nombre": nombre, "ID": cedula, "Entidad": entidad, "Fecha_Capsula": fecha_str, "mCI": dosis}
                        st.session_state.lista_local.append(nuevo)
                        st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")

# --- MÉTRICAS ---
c1, c2 = st.columns(2)
c1.metric("Total Programado", f"{round(dosis_actual, 2)} mCi")
c2.metric("Cupo Disponible", f"{round(restante, 2)} mCi")

if dosis_actual >= LIMITE_SEMANAL:
    st.warning("⚠️ Límite de 150 mCi alcanzado.")

st.divider()

# --- TABLA INTERACTIVA ---
if st.session_state.lista_local:
    st.subheader("Pacientes Programados")
    
    cols = st.columns([3, 2, 2, 2, 1, 1])
    cols[0].write("**Nombre**")
    cols[1].write("**ID**")
    cols[2].write("**Entidad**")
    cols[3].write("**Fecha**")
    cols[4].write("**mCI**")
    cols[5].write("**Acción**")

    for index, paciente in enumerate(st.session_state.lista_local):
        r = st.columns([3, 2, 2, 2, 1, 1])
        r[0].write(paciente.get('Nombre'))
        r[1].write(paciente.get('ID'))
        r[2].write(paciente.get('Entidad'))
        # Manejamos ambos nombres de columna posibles (de Drive o Local)
        f_val = paciente.get('Fecha_Capsula') or paciente.get('Fecha')
        r[3].write(f_val)
        r[4].write(paciente.get('mCI'))
        
        if r[5].button("🗑️", key=f"del_{index}"):
            st.session_state.lista_local.pop(index)
            # Nota: Al borrar aquí se borra de la vista y del PDF. 
            # Para borrar de Drive debe hacerse manualmente en el Excel.
            st.rerun()

    st.divider()
    pdf = generar_pdf(st.session_state.lista_local, dosis_actual)
    st.download_button("📥 Descargar Reporte PDF", pdf, "programacion.pdf", use_container_width=True)
    
    if st.button("🔄 Forzar Recarga desde Drive"):
        st.session_state.lista_local = cargar_datos_desde_drive()
        st.rerun()
else:
    st.info("No hay pacientes registrados. Si ya hay datos en Excel, pulsa 'Forzar Recarga'.")
