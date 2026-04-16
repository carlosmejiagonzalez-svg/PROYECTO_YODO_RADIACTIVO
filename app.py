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
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl="0s")
        # Limpiar espacios en blanco en los nombres de las columnas al cargar
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame(columns=["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCi"])

# Inicializar datos en la sesión
if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# === FUNCIÓN PARA GENERAR EL PDF ===
def generar_pdf_stream(df, total):
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
        except: pass
    
    elementos.append(Spacer(1, 40))

    # 2. Título
    titulo_estilo = estilos['Title']
    titulo_estilo.fontSize = 16
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES YODO RADIACTIVO</b>", titulo_estilo))
    elementos.append(Spacer(1, 20))

    # 3. Preparar datos para la tabla
    # Buscamos la columna de dosis dinámicamente para el PDF
    col_dosis_name = [c for c in df.columns if c.lower() == 'mci']
    c_mci = col_dosis_name[0] if col_dosis_name else 'mCi'

    data = [["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCi"]]
    for _, p in df.iterrows():
        data.append([
            str(p.get('Nombre', '')), 
            str(p.get('ID', '')), 
            str(p.get('Teléfono', '')), 
            str(p.get('Entidad', '')), 
            str(p.get('Edad', '')), 
            str(p.get('Diagnóstico', '')), 
            str(p.get('Fecha Cápsula', '')), 
            str(p.get(c_mci, '0'))
        ])
    
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

    # 4. Totales
    elementos.append(Spacer(1, 25))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    elementos.append(Paragraph(f"Reporte generado: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Italic']))

    doc.build(elementos)
    buffer.seek(0)
    return buffer

# === INTERFAZ DE USUARIO ===
st.title("☢️ Gestión de Medicina Nuclear")
st.markdown("---")

# Sidebar para ingreso
st.sidebar.header("📝 Registro de Paciente")
with st.sidebar.form("form_paciente", clear_on_submit=True):
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("Número de Identificación")
    tel = st.text_input("Teléfono de contacto")
    entidad = st.text_input("Entidad de Salud").upper()
    edad = st.number_input("Edad", min_value=0, max_value=110, step=1)
    diag = st.text_area("Diagnóstico Médico").upper()
    fecha_cap = st.date_input("Fecha toma de cápsula", value=datetime.now(colombia_tz))
    dosis = st.number_input("Dosis Requerida (mCi)", min_value=0.0, step=0.1, format="%.1f")
    
    submit = st.form_submit_button("Guardar en Lista")

# Lógica para añadir paciente
if submit:
    # Identificar columna mCi en el DF actual para mantener consistencia
    cols_actuales = [c.lower() for c in st.session_state.df_pacientes.columns]
    nombre_col_mci = "mCI" if "mci" not in cols_actuales else st.session_state.df_pacientes.columns[cols_actuales.index("mci")]

    total_actual = 0.0
    if not st.session_state.df_pacientes.empty:
        total_actual = st.session_state.df_pacientes[nombre_col_mci].sum()

    if not nombre or not cedula:
        st.sidebar.error("Ingrese Nombre e ID.")
    elif total_actual + dosis > 150.0:
        st.sidebar.error(f"Límite excedido. Cupo: {round(150.0 - total_actual, 2)} mCi.")
    else:
        nuevo_p = pd.DataFrame([{
            "Nombre": nombre, "ID": cedula, "Teléfono": tel, "Entidad": entidad,
            "Edad": edad, "Diagnóstico": diag, "Fecha Cápsula": fecha_cap.strftime("%d/%m/%Y"), 
            nombre_col_mci: dosis
        }])
        
        updated_df = pd.concat([st.session_state.df_pacientes, nuevo_p], ignore_index=True)
        conn.update(data=updated_df)
        st.session_state.df_pacientes = updated_df
        st.rerun()

# --- CÁLCULO DE TOTALES SEGURO ---
total_mci = 0.0
col_mci_key = "mCi" # default

if not st.session_state.df_pacientes.empty:
    st.session_state.df_pacientes.columns = [c.strip() for c in st.session_state.df_pacientes.columns]
    encontrada = [c for c in st.session_state.df_pacientes.columns if c.lower() == 'mci']
    if encontrada:
        col_mci_key = encontrada[0]
        total_mci = st.session_state.df_pacientes[col_mci_key].sum()

# Métricas
c_met1, c_met2 = st.columns(2)
c_met1.metric("Total Programado", f"{round(total_mci, 2)} mCi")
c_met2.metric("Cupo Disponible", f"{round(150.0 - total_mci, 2)} mCi")

# --- LISTADO Y ACCIONES ---
if not st.session_state.df_pacientes.empty:
    st.subheader("📋 Pacientes en lista")
    
    for i, row in st.session_state.df_pacientes.iterrows():
        col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
        col1.write(row['Nombre'])
        col2.write(row['ID'])
        col3.write(f"{row[col_mci_key]} mCi")
        if col4.button("🗑️", key=f"del_{i}"):
            st.session_state.df_pacientes.drop(i, inplace=True)
            conn.update(data=st.session_state.df_pacientes)
            st.rerun()
    
    st.divider()
    
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        pdf_data = generar_pdf_stream(st.session_state.df_pacientes, round(total_mci, 2))
        st.download_button(
            label="📥 Descargar PDF para Pedido",
            data=pdf_data,
            file_name=f"programacion_yodo_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with b_col2:
        if st.button("🚨 Limpiar Toda la Lista", use_container_width=True):
            # Crea un DF vacío con las mismas columnas
            vacio = pd.DataFrame(columns=st.session_state.df_pacientes.columns)
            conn.update(data=vacio)
            st.session_state.df_pacientes = vacio
            st.rerun()
else:
    st.info("No hay pacientes programados. Use el formulario de la izquierda.")