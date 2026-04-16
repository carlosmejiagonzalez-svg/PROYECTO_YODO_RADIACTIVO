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

# === CONFIGURACIÓN ===
st.set_page_config(page_title="Programación Yodo Radiactivo", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
RUTA_LOGO = "logo.png"

# === CONEXIÓN A GOOGLE SHEETS ===
# Esto leerá la configuración que pondremos en el panel de Streamlit
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        return conn.read(ttl="0s") # ttl=0s para que siempre traiga lo más reciente
    except:
        return pd.DataFrame(columns=["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCi"])

# Cargar datos al iniciar
if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# === FUNCIÓN PDF (Se mantiene igual) ===
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
    elementos.append(Spacer(1, 40))
    titulo_estilo = estilos['Title']
    titulo_estilo.fontSize = 16
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES YODO RADIACTIVO</b>", titulo_estilo))
    elementos.append(Spacer(1, 20))
    
    # Convertir DF a lista para la tabla
    data = [["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCi"]]
    for _, p in df.iterrows():
        data.append([p['Nombre'], p['ID'], p['Teléfono'], p['Entidad'], p['Edad'], p['Diagnóstico'], p['Fecha Cápsula'], p['mCi']])
    
    t = Table(data, colWidths=[110, 55, 65, 70, 30, 100, 75, 45])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 7),
    ]))
    elementos.append(t)
    elementos.append(Spacer(1, 25))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    elementos.append(Paragraph(f"Generado: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Italic']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# === INTERFAZ ===
st.title("☢️ Gestión de Medicina Nuclear (Conectado a Drive)")

# Registro en Sidebar
with st.sidebar.form("form_paciente"):
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID")
    tel = st.text_input("Teléfono")
    entidad = st.text_input("Entidad").upper()
    edad = st.number_input("Edad", 0, 110)
    diag = st.text_area("Diagnóstico").upper()
    fecha_cap = st.date_input("Fecha cápsula", value=datetime.now(colombia_tz))
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    if st.form_submit_button("Guardar en Drive"):
        total_actual = st.session_state.df_pacientes['mCi'].sum()
        if total_actual + dosis > 150.0:
            st.error("Límite excedido")
        else:
            nuevo_p = pd.DataFrame([{
                "Nombre": nombre, "ID": cedula, "Teléfono": tel, "Entidad": entidad,
                "Edad": edad, "Diagnóstico": diag, "Fecha Cápsula": fecha_cap.strftime("%d/%m/%Y"), "mCi": dosis
            }])
            # Actualizar Google Sheets
            updated_df = pd.concat([st.session_state.df_pacientes, nuevo_p], ignore_index=True)
            conn.update(data=updated_df)
            st.session_state.df_pacientes = updated_df
            st.rerun()

# Mostrar datos
total_mci = st.session_state.df_pacientes['mCi'].sum()
st.metric("Total Programado", f"{round(total_mci, 2)} mCi", f"{round(150-total_mci, 2)} restantes")

if not st.session_state.df_pacientes.empty:
    for i, row in st.session_state.df_pacientes.iterrows():
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
        c1.write(row['Nombre'])
        c2.write(row['ID'])
        c3.write(f"{row['mci']} mCi")
        if c4.button("🗑️", key=f"del_{i}"):
            st.session_state.df_pacientes.drop(i, inplace=True)
            conn.update(data=st.session_state.df_pacientes)
            st.rerun()
    
    pdf = generar_pdf_stream(st.session_state.df_pacientes, round(total_mci, 2))
    st.download_button("📥 Descargar PDF", pdf, f"pedido_{datetime.now(colombia_tz).strftime('%d_%m')}.pdf", "application/pdf")
    
    if st.button("🚨 Limpiar Todo"):
        conn.update(data=pd.DataFrame(columns=st.session_state.df_pacientes.columns))
        st.session_state.df_pacientes = cargar_datos()
        st.rerun()