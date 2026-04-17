import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# 1. Configuración de la Página
st.set_page_config(page_title="Generador PDF - Medicina Nuclear", page_icon="☢️")

# 2. Clase para el Formato del PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SOCIEDAD MÉDICO QUIRÚRGICA DEL ATLÁNTICO', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'Departamento de Medicina Nuclear', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# 3. Interfaz de Usuario
st.title("☢️ Registro y Generación de PDF")
st.write("Ingresa los datos del paciente para generar el reporte instantáneo.")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre del Paciente").upper()
        cedula = st.text_input("Cédula / ID")
    with col2:
        estudio = st.selectbox("Tipo de Estudio", ["Gammagrafía Ósea", "Gammagrafía Renal", "SPECT Cardiaco", "Otro"])
        dosis = st.number_input("Dosis Administrada (mCi)", min_value=0.0, step=0.1)

# 4. Botón para Generar PDF
if st.button("Generar Reporte PDF"):
    if nombre and cedula:
        # Crear PDF en memoria
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Contenido del reporte
        pdf.cell(200, 10, txt=f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="DATOS DEL PACIENTE", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Nombre: {nombre}", ln=True)
        pdf.cell(200, 10, txt=f"Identificación: {cedula}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="DETALLES DEL PROCEDIMIENTO", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Estudio: {estudio}", ln=True)
        pdf.cell(200, 10, txt=f"Dosis: {dosis} mCi", ln=True)
        
        pdf.ln(20)
        pdf.cell(200, 10, txt="_" * 30, ln=True, align='C')
        pdf.cell(200, 10, txt="Firma Responsable", ln=True, align='C')

        # Convertir a bytes para descarga
        pdf_output = pdf.output(dest='S').encode('latin-1')
        
        st.success("¡PDF Generado con éxito!")
        st.download_button(
            label="⬇️ Descargar Reporte",
            data=pdf_output,
            file_name=f"Reporte_{cedula}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("Por favor completa los datos del paciente.")

# 5. Tabla Local (Opcional - solo para ver lo que has hecho en la sesión)
st.divider()
st.info("Nota: Esta versión genera documentos individuales. No requiere conexión a base de datos externa.")
