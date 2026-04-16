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
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame(columns=["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCI"])
    except:
        return pd.DataFrame(columns=["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCI"])

# Inicializar datos
if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# === FUNCIÓN PDF ===
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

    data = [["Nombre", "ID", "Teléfono", "Entidad", "Edad", "Diagnóstico", "Fecha Cápsula", "mCi"]]
    
    col_mci = [c for c in df.columns if c.lower() == 'mci']
    key_mci = col_mci[0] if col_mci else 'mCI'

    for _, p in df.iterrows():
        data.append([
            str(p.get('Nombre', '')), str(p.get('ID', '')), str(p.get('Teléfono', '')),
            str(p.get('Entidad', '')), str(p.get('Edad', '')), str(p.get('Diagnóstico', '')),
            str(p.get('Fecha Cápsula', '')), str(p.get(key_mci, '0'))
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
    elementos.append(Spacer(1, 25))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    elementos.append(Paragraph(f"Generado: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Italic']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# === INTERFAZ ===
st.title("☢️ Gestión de Medicina Nuclear")

with st.sidebar.form("form_paciente", clear_on_submit=True):
    nombre = st.text_input("Nombre Completo").upper()
    cedula = st.text_input("ID")
    tel = st.text_input("Teléfono")
    entidad = st.text_input("Entidad").upper()
    edad = st.number_input("Edad", 0, 110)
    diag = st.text_area("Diagnóstico").upper()
    fecha_cap = st.date_input("Fecha cápsula", value=datetime.now(colombia_tz))
    dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
    submit = st.form_submit_button("Guardar en Lista")

if submit:
    if not nombre or not cedula:
        st.sidebar.error("Ingrese Nombre e ID.")
    else:
        # 1. Crear el nuevo registro
        nuevo_p = {
            "Nombre": nombre, "ID": cedula, "Teléfono": tel, "Entidad": entidad,
            "Edad": edad, "Diagnóstico": diag, "Fecha Cápsula": fecha_cap.strftime("%d/%m/%Y"), 
            "mCI": dosis
        }
        
        # 2. AGREGAR A LA LISTA EXISTENTE (Sin borrar lo anterior)
        # Convertimos el diccionario a DataFrame y lo pegamos al final
        df_nuevo = pd.DataFrame([nuevo_p])
        st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, df_nuevo], ignore_index=True)
        
        # 3. Intentar guardar en Drive
        try:
            conn.update(data=st.session_state.df_pacientes)
            st.sidebar.success(f"✅ Sincronizado: {nombre}")
        except:
            st.sidebar.warning("⚠️ Guardado en lista local (No se pudo enviar a Drive)")
        
        # Eliminamos el st.rerun() de aquí para que no refresque y borre la memoria local
        st.rerun()

# Totales
total_mci = 0.0
key_mci = "mCI"
if not st.session_state.df_pacientes.empty:
    st.session_state.df_pacientes.columns = [c.strip() for c in st.session_state.df_pacientes.columns]
    encontrada = [c for c in st.session_state.df_pacientes.columns if c.lower() == 'mci']
    if encontrada:
        key_mci = encontrada[0]
        total_mci = st.session_state.df_pacientes[key_mci].sum()

st.metric("Total Programado", f"{round(total_mci, 2)} mCi", f"{round(150-total_mci, 2)} disponibles")

# Tabla visual
if not st.session_state.df_pacientes.empty:
    for i, row in st.session_state.df_pacientes.iterrows():
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
        c1.write(row['Nombre'])
        c2.write(row['ID'])
        c3.write(f"{row.get(key_mci, 0)} mCi")
        if c4.button("🗑️", key=f"del_{i}"):
            st.session_state.df_pacientes = st.session_state.df_pacientes.drop(i).reset_index(drop=True)
            try:
                # Reemplaza tu bloque de "try...except" por este:
        try:
            # Forzamos a que escriba en la pestaña "Sheet1"
            conn.update(data=st.session_state.df_pacientes, worksheet="Sheet1")
            st.sidebar.success(f"✅ ¡Sincronizado en Excel!: {nombre}")
        except Exception as e:
            # Esto nos dirá el error exacto si vuelve a fallar
            st.sidebar.warning(f"⚠️ Error al guardar: {e}")
            except: pass
            st.rerun()
    
    st.divider()
    pdf = generar_pdf_stream(st.session_state.df_pacientes, round(total_mci, 2))
    st.download_button("📥 Descargar PDF", pdf, f"pedido_{datetime.now(colombia_tz).strftime('%d_%m')}.pdf", use_container_width=True)