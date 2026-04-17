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

# URL de tu Script (Verifica que sea la versión más reciente)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

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
    
    elementos.append(Paragraph("<b>REPORTE DE TRAZABILIDAD - NUCLEAR 2000 LTDA</b>", estilos['Title']))
    elementos.append(Paragraph(f"Fecha de Reporte: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    data = [["Paciente/ID", "Entidad", "Dosis", "Estado", "Recibido el", "Historial"]]
    for p in lista:
        data.append([
            f"{p['Nombre']}\nID: {p['ID']}", 
            p['Entidad'], 
            f"{p['mCI']} mCi", 
            p['Estado'], 
            p['Fecha_Recepcion'], 
            p['Notas']
        ])
    
    t = Table(data, colWidths=[120, 80, 50, 70, 90, 150])
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

st.title("☢️ Gestión Nuclear - Nuclear 2000 Ltda")
t1, t2, t3 = st.tabs(["📋 Pedidos", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- PESTAÑA 1: PEDIDOS ---
with t1:
    with st.sidebar.form("f1"):
        st.header("Nuevo Registro")
        n = st.text_input("Nombre").upper()
        i = st.text_input("Cédula / ID")
        e = st.text_input("Entidad").upper()
        d = st.number_input("mCi", 0.0)
        f = st.date_input("Fecha").strftime("%d/%m/%Y")
        if st.form_submit_button("Sincronizar"):
            requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
            st.session_state.lista_local = cargar_datos()
            st.rerun()
            
    if st.session_state.lista_local:
        df_p = pd.DataFrame(st.session_state.lista_local)[["Nombre", "ID", "Entidad", "mCI", "Estado"]]
        st.dataframe(df_p, use_container_width=True)
        
        st.divider()
        # BOTÓN RECUPERADO: LIMPIAR SEMANA
        if st.button("🚨 LIMPIAR PANTALLA (RESETEAR SEMANA)", use_container_width=True):
            requests.post(SCRIPT_URL)
            st.session_state.lista_local = []
            st.success("Base de datos limpia.")
            st.rerun()

# --- PESTAÑA 2: INVENTARIO ---
with t2:
    if st.session_state.lista_local:
        col_tit, col_pdf = st.columns([2, 1])
        col_tit.header("Control de Trazabilidad")
        
        # BOTÓN RECUPERADO: GENERAR PDF
        pdf_data = generar_pdf(st.session_state.lista_local)
        col_pdf.download_button("📄 GENERAR REPORTE PDF", data=pdf_data, 
                             file_name=f"reporte_nuclear_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
                             use_container_width=True)

        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | ID: {p['ID']} | {p['Estado']}"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"], 
                                 index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"].index(p.get('Estado', 'PENDIENTE')), key=f"e{idx}")
                not_val = str(p.get('Notas', '')) if str(p.get('Notas', '')).lower() != 'nan' else ""
                notas = c1.text_area("Notas", value=not_val, key=f"n{idx}")
                
                if c1.button("💾 Guardar", key=f"b{idx}"):
                    params = {"action":"update", "old_id":str(p['ID']).strip(), "id":str(p['ID']).strip(), "nombre":p['Nombre'], "entidad":p['Entidad'], "estado":est, "mci":p['mCI'], "notas":notas}
                    requests.get(SCRIPT_URL, params=params)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                if p.get('Estado') == "CANCELADO":
                    c2.info("Reasignar Dosis")
                    rn = c2.text_input("Nuevo Nombre", key=f"rn{idx}").upper()
                    ri = c2.text_input("Nueva ID", key=f"ri{idx}")
                    if c2.button("🔄 Ejecutar Reasignación", key=f"rb{idx}"):
                        hist = f"Original: {p['Nombre']} | ID: {p['ID']} | Motivo: {notas}"
                        requests.get(SCRIPT_URL, params={"action":"update","old_id":str(p['ID']).strip(),"id":str(ri).strip(),"nombre":rn,"entidad":p['Entidad'],"estado":"RECIBIDO","mci":p['mCI'],"notas":hist})
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()

# --- PESTAÑA 3: CALCULADORA ---
with t3:
    st.header("Calculadora Decaimiento (I-131)")
    # ... (Calculadora funcional)
