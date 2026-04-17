import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# 1. Configuración de la Página
st.set_page_config(page_title="Programación Yodo-131", page_icon="☢️", layout="wide")

# Inicializamos la lista de pacientes en la memoria de la sesión
if 'lista_yodo' not in st.session_state:
    st.session_state.lista_yodo = []

# 2. Clase para el PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'PROGRAMACIÓN DE PACIENTES - YODO 131', 0, 1, 'C')
        self.ln(10)

# 3. Interfaz de Usuario
st.title("📋 Gestión de Tratamientos Yodo-131")
st.warning("⚠️ Recordatorio de Seguridad: La dosis máxima permitida es de 150 mCi.")

with st.sidebar:
    st.header("Registrar Paciente")
    with st.form("registro", clear_on_submit=True):
        nombre = st.text_input("Nombre del Paciente").upper()
        cedula = st.text_input("Identificación / Cédula")
        dosis = st.number_input("Dosis Programada (mCi)", min_value=0.0, step=1.0)
        fecha_tratamiento = st.date_input("Fecha del Tratamiento")
        
        if st.form_submit_button("Añadir a la Lista"):
            # VALIDACIÓN DE DOSIS
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
    if st.button("📥 Descargar Lista en PDF"):
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(35, 10, "Fecha", 1)
        pdf.cell(80, 10, "Paciente", 1)
        pdf.cell(40, 10, "Cédula", 1)
        pdf.cell(30, 10, "mCi", 1)
        pdf.ln()
        
        pdf.set_font("Arial", size=11)
        for p in st.session_state.lista_yodo:
            pdf.cell(35, 10, p['Fecha'], 1)
            pdf.cell(80, 10, p['Paciente'], 1)
            pdf.cell(40, 10, p['Cédula'], 1)
            pdf.cell(30, 10, str(p['Dosis (mCi)']), 1)
            pdf.ln()
            
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        st.download_button(
            label="Confirmar Descarga",
            data=pdf_bytes,
            file_name=f"Programacion_Yodo_{datetime.now().strftime('%d_%m_%Y')}.pdf",
            mime="application/pdf"
        )
    
    if st.button("🗑️ Vaciar Lista"):
        st.session_state.lista_yodo = []
        st.rerun()
else:
    st.info("La lista está vacía.")
