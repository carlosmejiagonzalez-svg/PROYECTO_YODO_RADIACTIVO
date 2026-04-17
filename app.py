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

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Programación Yodo Radiactivo", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
RUTA_LOGO = "logo.png"

# --- LÓGICA DE DATOS LOCALES ---
# Inicializar la lista en la sesión del navegador si no existe
if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = pd.DataFrame(columns=[
        "Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCI"
    ])

# --- FUNCIÓN PARA GENERAR EL PDF ---
def generar_pdf_stream(df, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=30, rightMargin=30, topMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()

    # Agregar Logo si existe
    if os.path.exists(RUTA_LOGO):
        try:
            img = Image(RUTA_LOGO, width=120, height=60)
            img.hAlign = 'LEFT'
            elementos.append(img)
        except Exception:
            pass
    
    elementos.append(Spacer(1, 40))
    
    # Título
    titulo_estilo = estilos['Title']
    titulo_estilo.fontSize = 16
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES YODO RADIACTIVO</b>", titulo_estilo))
    elementos.append(Spacer(1, 20))

    # Tabla de Datos para el PDF
    data = [["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCI"]]
    for _, p in df.iterrows():
        data.append([
            str(p.get('Nombre', '')), str(p.get('ID', '')), str(p.get('Teléfono', '')),
            str(p.get('Entidad', '')), str(p.get('Edad', '')), str(p.get('Diagnóstico', '')),
            str(p.get('Fecha Cápsula', '')), str(p.get('mCI', '0'))
        ])
    
    t = Table(data, colWidths=[110, 55, 65, 70, 30, 100, 75, 45])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 7),
    ]))
    elementos.append(t)
    
    # Pie de página con el total
    elementos.append(Spacer(1, 25))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    elementos.append(Paragraph(f"Generado el: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Italic']))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# --- INTERFAZ DE USUARIO ---
st.title("☢️ Gestión de Medicina Nuclear - Local")

with st.sidebar.form("form_paciente", clear_on_submit=True):
    st.subheader("Registrar Paciente")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    tel = st.text_input("Teléfono")
    entidad = st.text_input("Entidad (EPS)").upper()
    edad = st.number_input("Edad", 0, 110)
    diag = st.text_area("Diagnóstico").upper()
    fecha_cap = st.date_input("Fecha de Cápsula", value=datetime.now(colombia_tz))
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    submit = st.form_submit_button("Añadir a Programación")

if submit:
    if not nombre or not cedula:
        st.sidebar.error("Error: El Nombre y el ID son obligatorios.")
    else:
        # Crear el nuevo registro
        nuevo_registro = pd.DataFrame([{
            "Nombre": nombre, "ID": cedula, "Teléfono": tel, "Entidad": entidad,
            "Edad": edad, "Diagnóstico": diag, "Fecha Cápsula": fecha_cap.strftime("%d/%m/%Y"), 
            "mCI": dosis
        }])
        
        # Actualizar la lista en memoria (Sesión)
        st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo_registro], ignore_index=True)
        st.sidebar.success(f"✅ Añadido a la lista: {nombre}")
        st.rerun()

# --- VISUALIZACIÓN Y CÁLCULOS ---
total_mci = 0.0
if not st.session_state.df_pacientes.empty:
    # Asegurar que mCI sea numérico para la suma
    total_mci = pd.to_numeric(st.session_state.df_pacientes['mCI'], errors='coerce').sum()

# Indicadores principales
c_met1, c_met2 = st.columns(2)
c_met1.metric("Total Dosis Programada", f"{round(total_mci, 2)} mCi")
c_met2.metric("Capacidad Restante (de 150mCi)", f"{round(150 - total_mci, 2)} mCi")

# Tabla interactiva en la App
if not st.session_state.df_pacientes.empty:
    st.subheader("Pacientes en la Programación Actual")
    
    # Mostrar registros con botón de eliminar
    for i, row in st.session_state.df_pacientes.iterrows():
        col_n, col_i, col_d, col_b = st.columns([4, 2, 2, 1])
        col_n.write(row['Nombre'])
        col_i.write(row['ID'])
        col_d.write(f"{row.get('mCI', 0)} mCi")
        
        if col_b.button("🗑️", key=f"btn_del_{i}"):
            st.session_state.df_pacientes = st.session_state.df_pacientes.drop(i).reset_index(drop=True)
            st.rerun()
    
    st.divider()
    
    # Botón para descargar el PDF
    pdf_file = generar_pdf_stream(st.session_state.df_pacientes, round(total_mci, 2))
    st.download_button(
        label="📥 Descargar Reporte PDF para Impresión",
        data=pdf_file,
        file_name=f"programacion_yodo_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    if st.button("🔴 Borrar toda la lista"):
        st.session_state.df_pacientes = pd.DataFrame(columns=st.session_state.df_pacientes.columns)
        st.rerun()
else:
    st.info("No hay pacientes registrados en la programación de esta semana.")
