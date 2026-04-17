import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import math
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
import os
from streamlit_gsheets import GSheetsConnection

# URL de tu Google Apps Script
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda - Gestión Avanzada", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
LIMITE_SEMANAL = 150.0

# Constante de decaimiento Yodo-131 (Vida media ~8.02 días)
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_desde_drive():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df.to_dict('records')
    except:
        pass
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos_desde_drive()

def calcular_decaimiento(actividad_inicial, horas_transcurridas):
    # Fórmula: A = A0 * e^(-ln(2) * t / t_1/2)
    # Convertimos vida media a horas para precisión
    hl_horas = HL_YODO * 24
    return actividad_inicial * math.exp(-math.log(2) * horas_transcurridas / hl_horas)

def generar_pdf(lista, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    
    logo_path = "logo.png" 
    if os.path.exists(logo_path):
        img = Image(logo_path, width=120, height=60)
        img.hAlign = 'CENTER'
        elementos.append(img)
        elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("<b>PROGRAMACIÓN DE PACIENTES - YODO 131</b>", estilos['Title']))
    elementos.append(Paragraph("<font size=12>Nuclear 2000 Ltda</font>", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    data = [["Nombre", "ID", "Entidad", "Fecha", "mCI"]]
    for p in lista:
        f_val = p.get('Fecha_Capsula') or p.get('Fecha') or ""
        data.append([p.get('Nombre',''), p.get('ID',''), p.get('Entidad',''), f_val, p.get('mCI', 0)])
    
    tabla = Table(data, colWidths=[160, 80, 100, 80, 50])
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTSIZE',(0,0),(-1,-1),10),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>TOTAL DOSIS PROGRAMADA: {total} mCi</b>", estilos['Normal']))
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# --- INTERFAZ PRINCIPAL ---
st.title("☢️ Gestión de Medicina Nuclear - Nuclear 2000 Ltda")

# Definición de Pestañas
tab1, tab2, tab3 = st.tabs(["📋 Programación y Pedidos", "📦 Inventario y Reasignación", "🧮 Calculadora de Decaimiento"])

# Cálculos globales
dosis_actual = sum(float(p.get('mCI', 0)) for p in st.session_state.lista_local)
restante = LIMITE_SEMANAL - dosis_actual

# --- TAB 1: PROGRAMACIÓN ---
with tab1:
    with st.sidebar.form("registro", clear_on_submit=True):
        st.header("Registrar Paciente")
        nombre = st.text_input("Nombre").upper()
        cedula = st.text_input("ID")
        entidad = st.text_input("Entidad").upper()
        dosis = st.number_input("Dosis (mCi)", 0.0, step=0.1)
        fecha = st.date_input("Fecha de Aplicación", value=datetime.now(colombia_tz))
        
        if st.form_submit_button("Sincronizar Pedido"):
            if nombre and cedula:
                if (dosis_actual + dosis) > LIMITE_SEMANAL:
                    st.sidebar.error(f"Límite superado. Cupo: {restante} mCi")
                else:
                    fecha_str = fecha.strftime("%d/%m/%Y")
                    params = {"nombre": nombre, "id": cedula, "entidad": entidad, "fecha": fecha_str, "mci": dosis}
                    st.session_state.lista_local.append({
                        "Nombre": nombre, "ID": cedula, "Entidad": entidad, 
                        "Fecha": fecha_str, "mCI": dosis, "Estado": "PENDIENTE"
                    })
                    try: requests.get(SCRIPT_URL, params=params, timeout=5)
                    except: pass
                    st.rerun()

    c1, c2 = st.columns(2)
    c1.metric("Total Programado", f"{round(dosis_actual, 2)} mCi")
    c2.metric("Cupo Disponible", f"{round(restante, 2)} mCi")

    if st.session_state.lista_local:
        df_prog = pd.DataFrame(st.session_state.lista_local)
        st.dataframe(df_prog[["Nombre", "ID", "Entidad", "Fecha", "mCI", "Estado"]], use_container_width=True)
        
        pdf = generar_pdf(st.session_state.lista_local, dosis_actual)
        st.download_button("📥 Descargar Reporte para Pedido", data=pdf, 
                           file_name=f"pedido_nuclear2000_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
                           use_container_width=True)
        
        if st.button("🚨 FINALIZAR SEMANA (Borrar Todo)", type="primary"):
            try: requests.post(SCRIPT_URL, timeout=10)
            except: pass
            st.session_state.lista_local = []
            st.rerun()

# --- TAB 2: INVENTARIO Y REASIGNACIÓN ---
with tab2:
    st.header("Gestión de Dosis Recibidas")
    if not st.session_state.lista_local:
        st.info("No hay dosis activas para gestionar.")
    else:
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} - {p['mCI']} mCi ({p['Estado']})"):
                col_a, col_b, col_c = st.columns(3)
                
                # Acciones de Estado
                nuevo_estado = col_a.selectbox("Cambiar Estado", 
                                             ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"],
                                             index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"].index(p['Estado']),
                                             key=f"st_{idx}")
                
                if col_a.button("Actualizar", key=f"btn_st_{idx}"):
                    st.session_state.lista_local[idx]['Estado'] = nuevo_estado
                    st.success(f"Estado de {p['Nombre']} actualizado.")
                    st.rerun()

                # Reasignación
                if p['Estado'] == "CANCELADO":
                    st.warning("Paciente canceló. Reasignar dosis a:")
                    nuevo_p = col_b.text_input("Nombre Nuevo Paciente", key=f"reas_{idx}")
                    nueva_id = col_b.text_input("ID Nuevo Paciente", key=f"id_reas_{idx}")
                    if col_b.button("Confirmar Reasignación", key=f"btn_reas_{idx}"):
                        st.session_state.lista_local[idx]['Nombre'] = nuevo_p.upper()
                        st.session_state.lista_local[idx]['ID'] = nueva_id
                        st.session_state.lista_local[idx]['Estado'] = "RECIBIDO"
                        st.session_state.lista_local[idx]['Notas'] = f"Reasignado de {p['Nombre']}"
                        st.rerun()

# --- TAB 3: CALCULADORA DE DECAIMIENTO ---
with tab3:
    st.header("Calculadora de Decaimiento (Yodo-131)")
    col1, col2 = st.columns(2)
    
    act_inicial = col1.number_input("Actividad Inicial (mCi)", 0.0, 500.0, 50.0)
    fecha_inicial = col1.date_input("Fecha de Medición Inicial", datetime.now(colombia_tz))
    hora_inicial = col1.time_input("Hora de Medición Inicial")
    
    fecha_final = col2.date_input("Fecha a Consultar", datetime.now(colombia_tz) + timedelta(days=1))
    hora_final = col2.time_input("Hora a Consultar")
    
    # Cálculo de tiempo transcurrido
    dt_inicial = datetime.combine(fecha_inicial, hora_inicial)
    dt_final = datetime.combine(fecha_final, hora_final)
    diferencia = dt_final - dt_inicial
    horas_transcurridas = diferencia.total_seconds() / 3600
    
    if horas_transcurridas < 0:
        st.error("La fecha de consulta debe ser posterior a la inicial.")
    else:
        act_final = calcular_decaimiento(act_inicial, horas_transcurridas)
        st.metric("Actividad Resultante", f"{round(act_final, 2)} mCi")
        st.info(f"Tiempo transcurrido: {round(horas_transcurridas/24, 2)} días")

if not st.session_state.lista_local:
    if st.button("🔄 Cargar datos de Drive"):
        st.session_state.lista_local = cargar_datos_desde_drive()
        st.rerun()
