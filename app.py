import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# 1. Configuración de la Página
st.set_page_config(page_title="Programación Yodo-131", page_icon="☢️", layout="wide")

# Inicializamos la lista de pacientes en la memoria de la sesión
if 'lista_yodo' not in st.session_state:
    st.session_state.lista_yodo = []

# 2. Clase para el PDF Profesional
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'PROGRAMACIÓN DE PACIENTES - YODO 131', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Reporte generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# 3. Interfaz de Usuario
st.title("📋 Gestión de Tratamientos Yodo-131")
st.warning("⚠️ Recordatorio de Seguridad: La dosis máxima permitida es de 150 mCi.")

with st.sidebar:
    st.header("Registrar Paciente")
    with st.form("registro", clear_on_submit=True):
        nombre = st.text_input("Nombre del Paciente").upper()
        cedula = st.text_input("Identificación / Cédula")
        # El límite de 150 se controla en la lógica de abajo
        dosis = st.number_input("Dosis Programada (mCi)", min_value=0.0, step=1.0)
        fecha_tratamiento = st.date_input("Fecha del Tratamiento")
        
        if st.form_submit_button("Añadir a la Lista"):
            # VALIDACIÓN CRÍTICA
            if dosis > 150.0:
                st.error(f"❌ ERROR: La dosis de {dosis} mCi excede el límite de 150 mCi.")
            elif nombre and cedula:
                paciente = {
                    "Fecha": fecha_tratamiento.strftime('%d/%m/%Y'),
                    "Paciente": nombre,
                    "Cédula": cedula,
                    "Dosis (mCi)": dosis
                }
                st.session_state.lista_yodo.append(paciente)
                st.success(f"Registrado: {nombre}")
            else:
                st.warning("⚠️ Completa Nombre y Cédula")

# 4. Tabla de Programación Visual
if st.session_state.lista_yodo:
    df = pd.DataFrame(st.session_state.lista_yodo)
    
    st.write("### Listado de Programación Actual")
    st.table(df)

    # 5. Generación de PDF
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Generar y Descargar PDF"):
            pdf = PDF()
            pdf.add_page()
            
            # Encabezados de tabla
            pdf.set_fill_color(200, 220, 255)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(35, 10, "Fecha", 1, 0, 'C', True)
            pdf.cell(80, 10, "Paciente", 1, 0, 'C', True)
            pdf.cell(40, 10, "Cédula", 1, 0, 'C', True)
            pdf.cell(30, 10, "mCi", 1, 1, 'C', True)
            
            # Datos
            pdf.set_font("Arial", size=11)
            for p in st.session_state.lista_yodo:
                pdf.cell(35, 10, p['Fecha'], 1)
                pdf.cell(80, 10, p['Paciente'], 1)
                pdf.cell(40, 10, p['Cédula'], 1)
                pdf.cell(30, 10, str(p['Dosis (mCi)']), 1)
                pdf.ln()
                
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            st.download_button(
                label="Confirmar Descarga de PDF",
                data=pdf_bytes,
                file_name=f"Programacion_Yodo_{datetime.now().strftime('%d_%m_%Y')}.pdf",
                mime="application/pdf"
            )
    
    with col2:
        if st.button("🗑️ Vaciar Lista"):
            st.session_state.lista_yodo = []
            st.rerun()
else:
    st.info("La lista está vacía. Comienza a programar pacientes desde el panel lateral.")
