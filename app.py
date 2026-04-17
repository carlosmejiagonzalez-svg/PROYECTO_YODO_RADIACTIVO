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

# URL de tu Google Apps Script (Asegúrate de haber implementado la versión con "action")
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda - Gestión Avanzada", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
LIMITE_SEMANAL = 150.0
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
        f_val = p.get('Fecha') or ""
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

# --- INTERFAZ ---
st.title("☢️ Gestión de Medicina Nuclear - Nuclear 2000 Ltda")

tab1, tab2, tab3 = st.tabs(["📋 Programación y Pedidos", "📦 Inventario y Reasignación", "🧮 Calculadora de Decaimiento"])

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
                fecha_str = fecha.strftime("%d/%m/%Y")
                params = {"action": "register", "nombre": nombre, "id": cedula, "entidad": entidad, "fecha": fecha_str, "mci": dosis}
                st.session_state.lista_local.append({
                    "Nombre": nombre, "ID": cedula, "Entidad": entidad, 
                    "Fecha": fecha_str, "mCI": dosis, "Estado": "PENDIENTE", "Notas": ""
                })
                try:
                    requests.get(SCRIPT_URL, params=params, timeout=5)
                except:
                    pass
                st.rerun()

    st.metric("Total Programado Semanal", f"{round(dosis_actual, 2)} mCi")
    
    if st.session_state.lista_local:
        df_prog = pd.DataFrame(st.session_state.lista_local)
        
        # Validación de columnas para evitar el KeyError
        for col in ["Nombre", "ID", "Entidad", "Fecha", "mCI", "Estado"]:
            if col not in df_prog.columns:
                df_prog[col] = "PENDIENTE" if col == "Estado" else ""
        
        st.dataframe(df_prog[["Nombre", "ID", "Entidad", "Fecha", "mCI", "Estado"]], use_container_width=True)
        
        pdf = generar_pdf(st.session_state.lista_local, dosis_actual)
        st.download_button("📥 Descargar Reporte PDF", data=pdf, 
                           file_name=f"pedido_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
                           use_container_width=True)
        
        if st.button("🚨 LIMPIAR SEMANA Y DRIVE", type="primary"):
            try:
                requests.post(SCRIPT_URL, timeout=10)
            except:
                pass
            st.session_state.lista_local = []
            st.rerun()

# --- TAB 2: INVENTARIO Y REASIGNACIÓN ---
with tab2:
    st.header("Gestión de Dosis y Escenarios")
    if not st.session_state.lista_local:
        st.info("No hay pacientes registrados.")
    else:
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} - {p['mCI']} mCi [{p.get('Estado', 'PENDIENTE')}]"):
                c1, c2 = st.columns(2)
                
                # Gestión de Estado y Notas
                nuevo_est = c1.selectbox("Cambiar Estado", 
                                       ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"],
                                       index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"].index(p.get('Estado', 'PENDIENTE')),
                                       key=f"est_{idx}")
                
                nuevas_notas = c1.text_area("Notas / Observaciones", value=p.get('Notas', ""), key=f"notas_{idx}")
                
                if c1.button("💾 Guardar Cambios", key=f"save_{idx}"):
                    params = {"action": "update", "id": p['ID'], "nombre": p['Nombre'], "estado": nuevo_est, "mci": p['mCI'], "notas": nuevas_notas}
                    try:
                        requests.get(SCRIPT_URL, params=params, timeout=5)
                        st.session_state.lista_local[idx]['Estado'] = nuevo_est
                        st.session_state.lista_local[idx]['Notas'] = nuevas_notas
                        st.success("Sincronizado con Drive")
                        st.rerun()
                    except:
                        st.error("Error al sincronizar")

                # Escenario de Reasignación
                if p.get('Estado') == "CANCELADO":
                    c2.warning("Reasignar dosis de este paciente:")
                    n_nom = c2.text_input("Nombre Nuevo Paciente", key=f"n_nom_{idx}").upper()
                    n_mci = c2.number_input("Dosis a entregar (mCi)", value=float(p['mCI']), key=f"n_mci_{idx}")
                    n_notas = c2.text_input("Notas de reasignación", value=f"Reasignado de {p['Nombre']}", key=f"n_not_{idx}")
                    
                    if c2.button("🔄 Confirmar Reasignación", key=f"btn_reas_{idx}"):
                        params = {"action": "update", "id": p['ID'], "nombre": n_nom, "estado": "RECIBIDO", "mci": n_mci, "notas": n_notas}
                        try:
                            requests.get(SCRIPT_URL, params=params, timeout=5)
                            st.session_state.lista_local[idx].update({
                                "Nombre": n_nom, "mCI": n_mci, "Estado": "RECIBIDO", "Notas": n_notas
                            })
                            st.rerun()
                        except:
                            st.error("Error en reasignación")

# --- TAB 3: CALCULADORA ---
with tab3:
    st.header("Cálculo de Decaimiento Radiactivo")
    col_i, col_f = st.columns(2)
    
    act_i = col_i.number_input("Actividad Inicial (mCi)", 0.0, 1000.0, 50.0)
    f_cal = col_i.date_input("Fecha de calibración", datetime.now(colombia_tz))
    h_cal = col_i.time_input("Hora de calibración")
    
    f_f = col_f.date_input("Fecha a Consultar", datetime.now(colombia_tz))
    h_f = col_f.time_input("Hora a Consultar")
    
    dt_i = datetime.combine(f_cal, h_cal)
    dt_f = datetime.combine(f_f, h_f)
    diff = (dt_f - dt_i).total_seconds() / 3600
    
    if diff < 0:
        st.error("La fecha de consulta debe ser posterior a la de calibración.")
    else:
        act_f = calcular_decaimiento(act_i, diff)
        st.metric("Actividad Resultante", f"{round(act_f, 2)} mCi")
        st.info(f"Tiempo transcurrido: {round(diff, 2)} horas")

if not st.session_state.lista_local:
    if st.button("🔄 Cargar datos de Drive"):
        st.session_state.lista_local = cargar_datos_desde_drive()
        st.rerun()
