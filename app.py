import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Gestión Medicina Nuclear - SMQA", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')

# 2. CONEXIÓN A GOOGLE SHEETS
# Se apoya en la URL configurada en la sección de Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # ttl=0 asegura que no use datos viejos guardados en memoria
        df = conn.read(ttl="0s")
        if df is not None and not df.empty:
            # Limpiar nombres de columnas por si acaso hay espacios invisibles
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except:
        pass
    # Estructura base si la hoja está vacía o falla la conexión
    return pd.DataFrame(columns=["Nombre", "ID", "Entidad", "Fecha Cápsula", "mCI"])

# Inicializar los datos en la sesión
if 'df_pacientes' not in st.session_state:
    st.session_state.df_pacientes = cargar_datos()

# 3. FUNCIÓN PARA GENERAR EL REPORTE PDF
def generar_pdf(df, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    
    # Encabezado del PDF
    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES - YODO 131</b>", estilos['Title']))
    elementos.append(Paragraph("Sociedad Médico Quirúrgica del Atlántico", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    # Preparar los datos de la tabla para ReportLab
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for _, p in df.iterrows():
        data.append([
            str(p.get('Nombre', '')), 
            str(p.get('ID', '')), 
            str(p.get('Entidad', '')), 
            str(p.get('Fecha Cápsula', '')), 
            str(p.get('mCI', '0'))
        ])
    
    # Estilo de la tabla
    tabla = Table(data, colWidths=[160, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ]))
    
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS SEMANAL: {total} mCi</b>", estilos['Normal']))
    elementos.append(Paragraph(f"Generado el: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Italic']))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# 4. INTERFAZ DE USUARIO (DASHBOARD)
st.title("☢️ Control de Medicina Nuclear - Atlántico")

# Formulario de registro en la barra lateral
with st.sidebar.form("registro_paciente", clear_on_submit=True):
    st.header("Registrar Paciente")
    nombre_in = st.text_input("Nombre Completo").upper()
    cedula_in = st.text_input("Cédula / ID")
    entidad_in = st.text_input("Entidad (EPS)").upper()
    dosis_in = st.number_input("Dosis a programar (mCi)", 0.0, step=0.1)
    fecha_in = st.date_input("Fecha de Cápsula", value=datetime.now(colombia_tz))
    
    if st.form_submit_button("Sincronizar con Google Sheets"):
        if nombre_in and cedula_in:
            # Crear el nuevo registro en un DataFrame temporal
            nuevo_paciente = pd.DataFrame([{
                "Nombre": nombre_in, 
                "ID": cedula_in, 
                "Entidad": entidad_in, 
                "Fecha Cápsula": fecha_in.strftime("%d/%m/%Y"), 
                "mCI": dosis_in
            }])
            
            # Actualizar el estado de la sesión
            st.session_state.df_pacientes = pd.concat([st.session_state.df_pacientes, nuevo_paciente], ignore_index=True)
            
            try:
                # ENVIAR ACTUALIZACIÓN A GOOGLE DRIVE
                conn.update(data=st.session_state.df_pacientes)
                st.sidebar.success("✅ ¡Sincronizado correctamente!")
                # Forzar limpieza de caché para que la app lea los datos nuevos
                st.cache_data.clear()
            except Exception as e:
                st.sidebar.error(f"⚠️ Error de sincronización: {e}")
            
            st.rerun()
        else:
            st.sidebar.error("Por favor completa Nombre e ID.")

# 5. VISUALIZACIÓN DE RESULTADOS
# Convertir mCI a numérico para evitar errores en la suma
df_display = st.session_state.df_pacientes.copy()
df_display['mCI'] = pd.to_numeric(df_display['mCI'], errors='coerce').fillna(0)
total_acumulado = df_display['mCI'].sum()

# Indicadores visuales
col_m1, col_m2 = st.columns(2)
col_m1.metric("Total Dosis Programada", f"{total_acumulado} mCi")
col_m2.metric("Capacidad Restante", f"{round(150 - total_acumulado, 2)} mCi")

st.divider()

if not df_display.empty:
    st.subheader("Listado de Programación Actual")
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # Botón para descargar reporte
    pdf_reporte = generar_pdf(df_display, total_acumulado)
    st.download_button(
        label="📥 Descargar Reporte PDF para Impresión",
        data=pdf_reporte,
        file_name=f"programacion_yodo_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    # Opción para limpiar la tabla (solo local)
    if st.button("🗑️ Borrar lista actual (Local)"):
        st.session_state.df_pacientes = pd.DataFrame(columns=["Nombre", "ID", "Entidad", "Fecha Cápsula", "mCI"])
        st.rerun()
else:
    st.info("No hay pacientes registrados en la programación actual.")
