import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import os
from streamlit_gsheets import GSheetsConnection

# URL de tu Google Apps Script
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Gestión Medicina Nuclear - Nuclear 2000 Ltda", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
LIMITE_SEMANAL = 150.0

# Conexión para lectura
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_desde_drive():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df.to_dict('records')
    except:
        pass
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos_desde_drive()

def generar_pdf(lista, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    
    # Logo
    logo_path = "logo.png" 
    if os.path.exists(logo_path):
        img = Image(logo_path, width=120, height=60)
        img.hAlign = 'CENTER'
        elementos.append(img)
        elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES - YODO 131</b>", estilos['Title']))
    elementos.append(Paragraph("<font size=12>Nuclear 2000 Ltda</font>", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for p in lista:
        f_val = p.get('Fecha_Capsula') or p.get('Fecha') or ""
        data.append([p.get('Nombre',''), p.get('ID',''), p.get('Entidad',''), f_val, p.get('mCI', 0)])
    
    tabla = Table(data, colWidths=[160, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTSIZE',(0,0),(-1,-1),10),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS PROGRAMADA: {total} mCi</b>", estilos['Normal']))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer

st.title("☢️ Control de Medicina Nuclear - Nuclear 2000 Ltda")

dosis_actual = sum(float(p.get('mCI', 0)) for p in st.session_state.lista_local)
restante = LIMITE_SEMANAL - dosis_actual

# Formulario lateral
with st.sidebar.form("registro", clear_on_submit=True):
    st.header("Registrar Paciente")
    nombre = st.text_input("Nombre").upper()
    cedula = st.text_input("ID")
    entidad = st.text_input("Entidad").upper()
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    fecha = st.date_input("Fecha", value=datetime.now(colombia_tz))
    
    if st.form_submit_button("Sincronizar con Drive"):
        if nombre and cedula:
            if (dosis_actual + dosis) > LIMITE_SEMANAL:
                st.sidebar.error(f"Límite superado. Cupo: {restante} mCi")
            else:
                fecha_str = fecha.strftime("%d/%m/%Y")
                params = {"nombre": nombre, "id": cedula, "entidad": entidad, "fecha": fecha_str, "mci": dosis}
                try:
                    requests.get(SCRIPT_URL, params=params)
                    st.session_state.lista_local.append({
                        "Nombre": nombre, "ID": cedula, "Entidad": entidad, 
                        "Fecha_Capsula": fecha_str, "mCI": dosis
                    })
                    st.rerun()
                except:
                    st.sidebar.error("Error al guardar en Drive")

# Métricas
c1, c2 = st.columns(2)
c1.metric("Total Programado", f"{round(dosis_actual, 2)} mCi")
c2.metric("Cupo Disponible", f"{round(restante, 2)} mCi")

if st.session_state.lista_local:
    # Tabla visual
    cols = st.columns([3, 2, 2, 2, 1, 1])
    for i, h in enumerate(["Nombre", "ID", "Entidad", "Fecha", "mCI", "Borrar"]):
        cols[i].write(f"**{h}**")

    for idx, p in enumerate(st.session_state.lista_local):
        r = st.columns([3, 2, 2, 2, 1, 1])
        r[0].write(p.get('Nombre'))
        r[1].write(p.get('ID'))
        r[2].write(p.get('Entidad'))
        r[3].write(p.get('Fecha_Capsula') or p.get('Fecha'))
        r[4].write(p.get('mCI'))
        if r[5].button("🗑️", key=f"del_{idx}"):
            st.session_state.lista_local.pop(idx)
            st.rerun()

    st.divider()
    
    # SECCIÓN DE CIERRE (LOS DOS PASOS)
    pdf = generar_pdf(st.session_state.lista_local, dosis_actual)
    
    st.download_button(
        label="📥 1. Descargar Reporte PDF",
        data=pdf,
        file_name=f"reporte_nuclear2000_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    if st.button("🚨 2. FINALIZAR SEMANA Y LIMPIAR DRIVE", use_container_width=True, type="primary"):
        try:
            # Petición POST para activar el borrado en Apps Script
            resp = requests.post(SCRIPT_URL)
            if resp.status_code == 200:
                st.session_state.lista_local = []
                st.success("✅ Datos borrados en Drive y pantalla limpia.")
                st.rerun()
            else:
                st.error("Error al comunicar con Google Sheets para el borrado.")
        except Exception as e:
            st.error(f"No se pudo completar el borrado: {e}")

else:
    if st.button("🔄 Cargar datos de Drive"):
        st.session_state.lista_local = cargar_datos_desde_drive()
        st.rerun()
