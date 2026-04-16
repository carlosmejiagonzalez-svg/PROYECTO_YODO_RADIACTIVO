import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz  # Librería para manejar zonas horarias
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io

# === CONFIGURACIÓN DE PÁGINA ===
st.set_page_config(page_title="Programación Yodo Radiactivo", layout="wide")

# Configurar Zona Horaria de Colombia
colombia_tz = pytz.timezone('America/Bogota')

# Inicializar estados de sesión
if 'pacientes' not in st.session_state:
    st.session_state.pacientes = []
if 'total_mci' not in st.session_state:
    st.session_state.total_mci = 0.0

# Nombre del archivo del logo en GitHub
RUTA_LOGO = "logo.png" 

# === FUNCIÓN PARA GENERAR EL PDF ===
def generar_pdf_stream(lista_pacientes, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=30, rightMargin=30, topMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()

    # 1. Logo
    if os.path.exists(RUTA_LOGO):
        try:
            img = Image(RUTA_LOGO, width=120, height=60)
            img.hAlign = 'LEFT'
            elementos.append(img)
        except:
            pass
    
    elementos.append(Spacer(1, 40))

    # 3. Título
    titulo_estilo = estilos['Title']
    titulo_estilo.fontSize = 16
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES YODO RADIACTIVO</b>", titulo_estilo))
    elementos.append(Spacer(1, 20))

    # 4. Tabla de datos
    data = [["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCi"]]
    for p in lista_pacientes:
        data.append([p['n'], p['id'], p['tel'], p['ent'], p['e'], p['d'], p['fecha'], p['mci']])
    
    t = Table(data, colWidths=[110, 55, 65, 70, 30, 100, 75, 45])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elementos.append(t)

    # 5. Totales con Fecha de Colombia
    fecha_colombia = datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')
    elementos.append(Spacer(1, 25))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    elementos.append(Paragraph(f"Reporte generado el: {fecha_colombia} (Hora Colombia)", estilos['Italic']))

    doc.build(elementos)
    buffer.seek(0)
    return buffer

# === INTERFAZ DE USUARIO (STREAMLIT) ===
st.title("☢️ Gestión de Medicina Nuclear")
st.markdown("---")

st.sidebar.header("📝 Registro de Paciente")
with st.sidebar.form("form_paciente", clear_on_submit=True):
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("Número de Identificación")
    tel = st.text_input("Teléfono de contacto")
    entidad = st.text_input("Entidad de Salud").upper()
    edad = st.number_input("Edad", min_value=0, max_value=110, step=1)
    diag = st.text_area("Diagnóstico Médico").upper()
    
    # Fecha de toma predeterminada a hoy en Colombia
    fecha_cap = st.date_input("Fecha toma de cápsula", value=datetime.now(colombia_tz))
    
    dosis = st.number_input("Dosis Requerida (mCi)", min_value=0.0, step=0.1, format="%.1f")
    
    submit = st.form_submit_button("Añadir a la lista")

if submit:
    if not nombre or not cedula:
        st.sidebar.error("Por favor ingrese Nombre e Identificación.")
    elif st.session_state.total_mci + dosis > 150.0:
        st.sidebar.error(f"❌ Límite excedido. Solo quedan {round(150.0 - st.session_state.total_mci, 2)} mCi.")
    else:
        nuevo_p = {
            "n": nombre, "id": cedula, "tel": tel, "ent": entidad,
            "e": edad, "d": diag, "fecha": fecha_cap.strftime("%d/%m/%Y"), "mci": dosis
        }
        st.session_state.pacientes.append(nuevo_p)
        st.session_state.total_mci += dosis
        st.sidebar.success(f"✅ Agregado: {nombre}")

col_stats1, col_stats2 = st.columns(2)
with col_stats1:
    st.metric("Total Dosis Programada", f"{round(st.session_state.total_mci, 2)} mCi")
with col_stats2:
    disponible = round(150.0 - st.session_state.total_mci, 2)
    st.metric("Cupo Disponible", f"{disponible} mCi")

st.subheader("📋 Lista de Pacientes")

if st.session_state.pacientes:
    h_col1, h_col2, h_col3, h_col4 = st.columns([4, 2, 2, 1])
    h_col1.write("**Paciente**")
    h_col2.write("**ID**")
    h_col3.write("**Dosis**")
    h_col4.write("**Acción**")
    
    for i, p in enumerate(st.session_state.pacientes):
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
        c1.write(p['n'])
        c2.write(p['id'])
        c3.write(f"{p['mci']} mCi")
        if c4.button("🗑️", key=f"del_{i}"):
            st.session_state.total_mci -= p['mci']
            st.session_state.pacientes.pop(i)
            st.rerun()
    
    st.markdown("---")
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        pdf_data = generar_pdf_stream(st.session_state.pacientes, round(st.session_state.total_mci, 2))
        nombre_pdf = f"programacion_yodo_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf"
        st.download_button(
            label="📥 Descargar Programación (PDF)",
            data=pdf_data,
            file_name=nombre_pdf,
            mime="application/pdf",
            use_container_width=True
        )
    
    with btn_col2:
        if st.button("🚨 Limpiar Toda la Semana", use_container_width=True):
            st.session_state.pacientes = []
            st.session_state.total_mci = 0.0
            st.rerun()
else:
    st.info("Aún no se han ingresado pacientes.")