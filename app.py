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

def generar_pdf(lista, titulo="REPORTE DE TRAZABILIDAD"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    elementos.append(Paragraph(f"<b>{titulo} - NUCLEAR 2000 LTDA</b>", estilos['Title']))
    elementos.append(Paragraph(f"Generado el: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))
    elementos.append(Spacer(1, 15))
    
    data = [["Paciente", "ID", "Entidad", "Dosis", "Estado", "Fecha Rec."]]
    for p in lista:
        data.append([p['Nombre'], p['ID'], p['Entidad'], f"{p['mCI']} mCi", p['Estado'], p['Fecha_Recepcion']])
    
    t = Table(data, colWidths=[130, 70, 80, 50, 70, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),8),
    ]))
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

t1, t2, t3 = st.tabs(["📋 Programación", "📦 Inventario", "🧮 Calculadora"])

# --- TAB 1: PROGRAMACIÓN ---
with t1:
    col_f, col_v = st.columns([1, 2])
    with col_f:
        st.subheader("📝 Nuevo Registro")
        with st.form("registro_limpio", clear_on_submit=True):
            n = st.text_input("Nombre").upper()
            i = st.text_input("Cédula")
            e = st.text_input("Entidad").upper()
            d = st.number_input("Dosis (mCi)", 0.0)
            f = st.date_input("Fecha Aplicación").strftime("%d/%m/%Y")
            if st.form_submit_button("Sincronizar"):
                requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
                st.session_state.lista_local = cargar_datos()
                st.rerun()
        
        # BOTÓN DE LIMPIEZA TOTAL RECUPERADO
        st.divider()
        if st.button("🚨 LIMPIAR PANTALLA / RESET SEMANA", use_container_width=True):
            requests.post(SCRIPT_URL)
            st.session_state.lista_local = []
            st.rerun()

    with col_v:
        st.subheader("📊 Inventario Programado")
        if st.session_state.lista_local:
            df = pd.DataFrame(st.session_state.lista_local)
            prog = df[df['Estado'] != 'CANCELADO']['mCI'].apply(pd.to_numeric).sum()
            st.metric("Total Dosis Programada", f"{prog} mCi")
            st.dataframe(df[["Nombre", "ID", "mCI", "Estado"]], use_container_width=True)

# --- TAB 2: INVENTARIO ---
with t2:
    if st.session_state.lista_local:
        c_t, c_b = st.columns([2, 1])
        c_t.header("Control de Dosis")
        
        # BOTÓN GENERAR RESUMEN GENERAL
        resumen_pdf = generar_pdf(st.session_state.lista_local, "RESUMEN GENERAL DE INVENTARIO")
        c_b.download_button("📄 GENERAR RESUMEN (PDF)", data=resumen_pdf, 
                             file_name=f"resumen_{datetime.now().strftime('%d_%m')}.pdf", use_container_width=True)

        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                col1, col2 = st.columns(2)
                
                # Actualización de Estado
                est = col1.selectbox("Cambiar Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"], 
                                   index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO"].index(p.get('Estado', 'PENDIENTE')), key=f"e{idx}")
                not_v = str(p.get('Notas', '')) if str(p.get('Notas', '')).lower() != 'nan' else ""
                obs = col1.text_area("Observaciones", value=not_v, key=f"n{idx}")
                
                if col1.button("💾 Guardar", key=f"b{idx}"):
                    requests.get(SCRIPT_URL, params={"action":"update", "old_id":str(p['ID']).strip(), "estado":est, "notas":obs})
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                # Reasignación con formulario completo
                if p.get('Estado') == "CANCELADO":
                    col2.warning("Reasignación de Dosis")
                    rn = col2.text_input("Nuevo Nombre", key=f"rn{idx}").upper()
                    ri = col2.text_input("Nueva ID", key=f"ri{idx}")
                    re = col2.text_input("Entidad (Heredada)", value=p['Entidad'], key=f"re{idx}").upper()
                    if col2.button("🔄 Confirmar Reasignación", key=f"rb{idx}"):
                        hist = f"Original: {p['Nombre']}. Motivo: {obs}"
                        # Pasamos todos los datos técnicos del paciente original
                        params = {
                            "action": "reasignar",
                            "old_id": str(p['ID']).strip(),
                            "nombre": rn, "id": ri, "entidad": re,
                            "mci": p['mCI'], "fecha": p['Fecha_Capsula'],
                            "notas": hist
                        }
                        requests.get(SCRIPT_URL, params=params)
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()

# --- TAB 3: CALCULADORA ---
with t3:
    st.header("🧮 Calculadora de Decaimiento")
    c1, c2 = st.columns(2)
    ai = c1.number_input("Actividad Inicial", value=100.0)
    fc = c1.date_input("Fecha Calibración")
    hc = c1.time_input("Hora Calibración")
    ff = c2.date_input("Fecha Futura")
    hf = c2.time_input("Hora Futura")
    
    dt1 = datetime.combine(fc, hc)
    dt2 = datetime.combine(ff, hf)
    h = (dt2 - dt1).total_seconds() / 3600
    if h >= 0:
        af = ai * math.exp(-math.log(2) * h / (HL_YODO * 24))
        st.metric("Resultado", f"{round(af, 2)} mCi")
    else: st.error("La fecha debe ser posterior.")
