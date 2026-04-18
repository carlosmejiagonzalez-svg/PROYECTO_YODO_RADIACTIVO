import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# URL de tu Script
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 # Vida media Yodo-131

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            columnas = ["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI", "Estado", "Fecha_Recepcion", "mCI_Real", "Notas"]
            for c in columnas:
                if c not in df.columns: df[c] = ""
            return df.to_dict('records')
    except: pass
    return []

def generar_pdf(lista):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    elementos.append(Paragraph("<b>REPORTE DE PROGRAMACIÓN Y TRAZABILIDAD - NUCLEAR 2000 LTDA</b>", estilos['Title']))
    elementos.append(Paragraph(f"Generado el: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))
    elementos.append(Spacer(1, 15))
    
    data = [["Paciente", "ID", "Entidad", "Dosis", "Estado", "Notas"]]
    for p in lista:
        data.append([p['Nombre'], p['ID'], p['Entidad'], f"{p['mCI']} mCi", p['Estado'], p['Notas']])
    
    t = Table(data, colWidths=[130, 70, 80, 50, 70, 160])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),7),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

t1, t2, t3 = st.tabs(["📋 Programación", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- TAB 1: PROGRAMACIÓN ---
with t1:
    col_form, col_view = st.columns([1, 2])
    
    with col_form:
        st.subheader("📝 Nuevo Registro")
        # Usamos st.form con clear_on_submit=True para limpiar los campos automáticamente
        with st.form("form_registro", clear_on_submit=True):
            n = st.text_input("Nombre del Paciente").upper()
            i = st.text_input("Cédula / ID")
            e = st.text_input("Entidad").upper()
            d = st.number_input("Dosis (mCi)", 0.0, step=1.0)
            f = st.date_input("Fecha de Aplicación").strftime("%d/%m/%Y")
            
            if st.form_submit_button("Sincronizar Pedido"):
                if n and i:
                    requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

    with col_view:
        st.subheader("📊 Resumen de Programación")
        if st.session_state.lista_local:
            df = pd.DataFrame(st.session_state.lista_local)
            
            # --- CONTADOR DE YODO ---
            total_prog = df[df['Estado'] != 'CANCELADO']['mCI'].apply(pd.to_numeric, errors='coerce').sum()
            stock_inicial = 500.0 # Ajusta este valor según tu inventario semanal
            disponible = stock_inicial - total_prog
            
            c_a, c_b = st.columns(2)
            c_a.metric("Total Programado", f"{total_prog} mCi", delta_color="inverse")
            c_b.metric("Disponible", f"{disponible} mCi")
            
            st.dataframe(df[["Nombre", "ID", "mCI", "Estado"]], use_container_width=True)
            
            # Botón PDF en esta pestaña
            pdf_p = generar_pdf(st.session_state.lista_local)
            st.download_button("📄 Descargar Pedido PDF", data=pdf_p, 
                               file_name=f"pedido_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True)

# --- TAB 2: INVENTARIO ---
with t2:
    if st.session_state.lista_local:
        st.header("Control de Estados")
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"], 
                                 index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"].index(p.get('Estado', 'PENDIENTE')), key=f"e{idx}")
                not_v = str(p.get('Notas', '')) if str(p.get('Notas', '')).lower() != 'nan' else ""
                notas = c1.text_area("Observaciones", value=not_v, key=f"n{idx}")
                
                if c1.button("💾 Guardar", key=f"b{idx}"):
                    requests.get(SCRIPT_URL, params={"action":"update", "old_id":str(p['ID']).strip(), "estado":est, "notas":notas})
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                if p.get('Estado') == "CANCELADO":
                    rn = c2.text_input("Nuevo Paciente", key=f"rn{idx}").upper()
                    ri = c2.text_input("Nueva ID", key=f"ri{idx}")
                    if c2.button("🔄 Reasignar Dosis", key=f"rb{idx}"):
                        hist = f"Dosis de: {p['Nombre']}. Motivo: {notas}"
                        requests.get(SCRIPT_URL, params={"action":"reasignar","old_id":str(p['ID']).strip(),"nombre":rn,"id":ri,"entidad":p['Entidad'],"mci":p['mCI'],"fecha":p['Fecha_Capsula'],"notas":hist})
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()

# --- TAB 3: CALCULADORA ---
with t3:
    st.header("🧮 Calculadora de Decaimiento Radiactivo")
    col1, col2 = st.columns(2)
    
    act_i = col1.number_input("Actividad Inicial (mCi)", value=100.0)
    f_cal = col1.date_input("Fecha Calibración")
    h_cal = col1.time_input("Hora Calibración")
    
    f_fut = col2.date_input("Fecha a Calcular")
    h_fut = col2.time_input("Hora a Calcular")
    
    dt_i = datetime.combine(f_cal, h_cal)
    dt_f = datetime.combine(f_fut, h_fut)
    
    horas = (dt_f - dt_i).total_seconds() / 3600
    
    if horas >= 0:
        # Fórmula: A = Ao * e^(-ln2 * t / T1/2)
        act_f = act_i * math.exp(-math.log(2) * horas / (HL_YODO * 24))
        st.metric("Actividad Resultante", f"{round(act_f, 2)} mCi")
        st.info(f"Tiempo transcurrido: {round(horas, 1)} horas.")
    else:
        st.error("La fecha futura debe ser posterior a la de calibración.")
