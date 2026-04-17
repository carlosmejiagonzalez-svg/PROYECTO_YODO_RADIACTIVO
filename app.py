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
st.set_page_config(page_title="Programación Yodo Radiactivo", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
RUTA_LOGO = "logo.png"

# --- CONEXIÓN SIMPLIFICADA ---
# Al ser pública, solo necesita la URL que pusiste en Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # Intentamos leer la hoja
        df = conn.read(ttl="0s")
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception as e:
        st.error(f"Error al conectar con la hoja: {e}")
    return pd.DataFrame(columns=["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCI"])

if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# --- FUNCIÓN PDF (ReportLab) ---
def generar_pdf_stream(df, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=30, rightMargin=30, topMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()

    if os.path.exists(RUTA_LOGO):
        try:
            img = Image(RUTA_LOGO, width=120, height=60)
            img.hAlign = 'LEFT'
            elementos.append(img)
        except: pass
    
    elementos.append(Spacer(1, 30))
    titulo_estilo = estilos['Title']
    titulo_estilo.fontSize = 16
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES YODO RADIACTIVO</b>", titulo_estilo))
    elementos.append(Spacer(1, 20))

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
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS: {total} mCi</b>", estilos['Normal']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# --- INTERFAZ ---
st.title("☢️ Gestión Medicina Nuclear - Barranquilla")

with st.sidebar.form("form_paciente", clear_on_submit=True):
    st.subheader("Nuevo Registro")
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID / Cédula")
    tel = st.text_input("Teléfono")
    entidad = st.text_input("Entidad").upper()
    edad = st.number_input("Edad", 0, 110)
    diag = st.text_area("Diagnóstico").upper()
    fecha_cap = st.date_input("Fecha de Cápsula", value=datetime.now(colombia_tz))
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    submit = st.form_submit_button("Guardar")

if submit:
    if nombre and cedula:
        if dosis > 150.0:
            st.sidebar.error("Límite excedido (Máx 150 mCi)")
        else:
            nuevo = pd.DataFrame([{
                "Nombre": nombre, "ID": cedula, "Teléfono": tel, "Entidad": entidad,
                "Edad": edad, "Diagnóstico": diag, "Fecha Cápsula": fecha_cap.strftime("%d/%m/%Y"), 
                "mCI": dosis
            }])
            st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo], ignore_index=True)
            try:
                # Sincronizar con la hoja pública
                conn.update(data=st.session_state.df_pacientes)
                st.sidebar.success("Sincronizado con Google Sheets")
            except Exception as e:
                st.sidebar.warning(f"Guardado localmente. Error sync: {e}")
            st.rerun()

# --- TABLA Y PDF ---
total_mci = pd.to_numeric(st.session_state.df_pacientes['mCI'], errors='coerce').sum()
st.metric("Total Programado", f"{round(total_mci, 2)} mCi", f"{round(150-total_mci, 2)} disponibles")

if not st.session_state.df_pacientes.empty:
    for i, row in st.session_state.df_pacientes.iterrows():
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
        c1.write(row['Nombre'])
        c2.write(row['ID'])
        c3.write(f"{row.get('mCI', 0)} mCi")
        if c4.button("🗑️", key=f"del_{i}"):
            st.session_state.df_pacientes = st.session_state.df_pacientes.drop(i).reset_index(drop=True)
            try: conn.update(data=st.session_state.df_pacientes)
            except: pass
            st.rerun()
    
    pdf = generar_pdf_stream(st.session_state.df_pacientes, round(total_mci, 2))
    st.download_button("📥 Descargar Reporte PDF", pdf, "programacion.pdf", use_container_width=True)
