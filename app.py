import streamlit as st
import pandas as pd
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io

# Configuración de la página
st.set_page_config(page_title="Gestión Medicina Nuclear", layout="wide")

# Inicializar el estado de la aplicación (esto evita que los datos se borren al recargar)
if 'pacientes' not in st.session_state:
    st.session_state.pacientes = []
if 'total_mci' not in st.session_state:
    st.session_state.total_mci = 0.0

RUTA_LOGO = "logo.png" # En GitHub/Streamlit, subiremos el logo a la misma carpeta

def generar_pdf_stream(lista_pacientes, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=30, rightMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()

    if os.path.exists(RUTA_LOGO):
        img = Image(RUTA_LOGO, width=120, height=60)
        img.hAlign = 'LEFT'
        elementos.append(img)
    
    elementos.append(Spacer(1, 40))
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES YODO RADIACTIVO</b>", estilos['Title']))
    elementos.append(Spacer(1, 20))

    data = [["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCi"]]
    for p in lista_pacientes:
        data.append([p['n'], p['id'], p['tel'], p['ent'], p['e'], p['d'], p['fecha'], p['mci']])
    
    t = Table(data, colWidths=[100, 55, 65, 70, 30, 110, 75, 40])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 7),
    ]))
    elementos.append(t)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS: {total} mCi</b>", estilos['Normal']))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# --- INTERFAZ DE STREAMLIT ---
st.title("☢️ Programación de Yodo Radiactivo")
st.sidebar.header("Registro de Paciente")

with st.sidebar.form("formulario_paciente", clear_on_submit=True):
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("Identificación")
    telefono = st.text_input("Teléfono")
    entidad = st.text_input("Entidad de Salud").upper()
    edad = st.number_input("Edad", min_value=0, max_value=120)
    diag = st.text_area("Diagnóstico").upper()
    fecha_cap = st.date_input("Fecha toma de cápsula")
    dosis = st.number_input("Dosis (mCi)", min_value=0.1, step=0.1)
    
    boton_agregar = st.form_submit_button("Agregar Paciente")

if boton_agregar:
    if st.session_state.total_mci + dosis > 150.0:
        st.error(f"❌ Límite excedido. Solo quedan {150.0 - st.session_state.total_mci} mCi.")
    else:
        st.session_state.pacientes.append({
            "n": nombre, "id": cedula, "tel": telefono, "ent": entidad,
            "e": edad, "d": diag, "fecha": fecha_cap.strftime("%d/%m/%Y"), "mci": dosis
        })
        st.session_state.total_mci += dosis
        st.success(f"✅ {nombre} agregado.")

# Mostrar Datos
st.metric("Total Dosis Semanal", f"{st.session_state.total_mci} mCi", f"{150 - st.session_state.total_mci} mCi restantes")

if st.session_state.pacientes:
    df = pd.DataFrame(st.session_state.pacientes)
    st.table(df)
    
    if st.button("Limpiar Lista"):
        st.session_state.pacientes = []
        st.session_state.total_mci = 0.0
        st.rerun()

    pdf_file = generar_pdf_stream(st.session_state.pacientes, st.session_state.total_mci)
    st.download_button(
        label="📥 Descargar Pedido PDF",
        data=pdf_file,
        file_name=f"pedido_yodo_{datetime.now().strftime('%d_%m_%Y')}.pdf",
        mime="application/pdf"
    )