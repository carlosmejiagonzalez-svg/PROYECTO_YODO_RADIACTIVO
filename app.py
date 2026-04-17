import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
import os
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# URL de tu Script (Asegúrate de que sea la última implementación)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"

st.set_page_config(page_title="Nuclear 2000 Ltda - Trazabilidad Total", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            # Mapeo de columnas según tu Google Sheet
            columnas = ["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI", "Estado", "Fecha_Recepcion", "mCI_Real", "Notas"]
            for c in columnas:
                if c not in df.columns: df[c] = ""
            return df.to_dict('records')
    except: pass
    return []

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

def generar_pdf(lista):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    estilos = getSampleStyleSheet()
    elementos.append(Paragraph("<b>REPORTE DE TRAZABILIDAD - NUCLEAR 2000 LTDA</b>", estilos['Title']))
    elementos.append(Paragraph(f"Fecha: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))
    elementos.append(Spacer(1, 20))
    
    data = [["Paciente/ID", "Entidad", "mCI", "Estado", "Recibido", "Historial"]]
    for p in lista:
        # Usamos .get() por seguridad si alguna celda está vacía
        data.append([
            f"{p.get('Nombre','')}\n{p.get('ID','')}", 
            p.get('Entidad',''), 
            p.get('mCI',''), 
            p.get('Estado',''), 
            p.get('Fecha_Recepcion',''), 
            p.get('Notas','')
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

st.title("☢️ Sistema de Gestión Nuclear - Nuclear 2000 Ltda")
tab1, tab2, tab3 = st.tabs(["📋 Programación", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- TAB 1: PROGRAMACIÓN ---
with tab1:
    with st.sidebar.form("registro", clear_on_submit=True):
        st.header("Nuevo Pedido")
        n_nom = st.text_input("Nombre del Paciente").upper()
        n_ced = st.text_input("Cédula / ID")
        n_ent = st.text_input("Entidad").upper()
        n_mci = st.number_input("Dosis mCI", 0.0, step=0.1)
        n_fec = st.date_input("Fecha Aplicación").strftime("%d/%m/%Y")
        
        if st.form_submit_button("Sincronizar Pedido"):
            if n_nom and n_ced:
                params = {
                    "action": "register", 
                    "nombre": n_nom, 
                    "id": str(n_ced).strip(), 
                    "entidad": n_ent, 
                    "mci": n_mci, 
                    "fecha": n_fec
                }
                requests.get(SCRIPT_URL, params=params, timeout=10)
                st.session_state.lista_local = cargar_datos()
                st.rerun()

    if st.session_state.lista_local:
        df_p = pd.DataFrame(st.session_state.lista_local)[["Nombre", "ID", "Entidad", "mCI", "Estado"]]
        st.dataframe(df_p, use_container_width=True)
        
        st.divider()
        if st.button("🚨 LIMPIAR SEMANA (BORRADO TOTAL)", use_container_width=True):
            requests.post(SCRIPT_URL, timeout=10)
            st.session_state.lista_local = []
            st.rerun()

# --- TAB 2: INVENTARIO Y REASIGNACIÓN ---
with tab2:
    c_inv, c_rep = st.columns([2, 1])
    c_inv.header("Control de Dosis")
    
    if st.session_state.lista_local:
        # Reporte PDF
        pdf_data = generar_pdf(st.session_state.lista_local)
        c_rep.download_button("📄 DESCARGAR REPORTE SEMANAL", data=pdf_data, 
                             file_name=f"reporte_{datetime.now(colombia_tz).strftime('%d_%m_%Y')}.pdf",
                             use_container_width=True)

        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | Estado: {p['Estado']}"):
                col_x, col_y = st.columns(2)
                
                # Gestión de Estado y Notas (Mantiene historial)
                n_est = col_x.selectbox("Cambiar Estado", ["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"], 
                                      index=["PENDIENTE", "RECIBIDO", "APLICADO", "CANCELADO", "DECAIMIENTO"].index(p.get('Estado', 'PENDIENTE')), 
                                      key=f"st_{idx}")
                
                # n_not contendrá lo que ya esté en la celda (como el historial de reasignación)
                n_not = col_x.text_area("Notas / Trazabilidad", value=p.get('Notas', ""), key=f"nt_{idx}")
                
                if col_x.button("💾 Guardar y Cerrar", key=f"sv_{idx}"):
                    params = {
                        "action": "update", 
                        "old_id": str(p['ID']).strip(), 
                        "id": str(p['ID']).strip(), 
                        "nombre": p['Nombre'], 
                        "entidad": p['Entidad'], 
                        "estado": n_est, 
                        "mci": p['mCI'], 
                        "notas": n_not # Enviamos las notas (historial incluido)
                    }
                    requests.get(SCRIPT_URL, params=params, timeout=15)
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

                # Reasignación Total
                if p.get('Estado') == "CANCELADO":
                    col_y.info("Formulario de Reasignación")
                    r_nom = col_y.text_input("Nuevo Paciente", key=f"rn_{idx}").upper()
                    r_ced = col_y.text_input("Nueva ID", key=f"ri_{idx}")
                    r_ent = col_y.text_input("Nueva Entidad", key=f"re_{idx}").upper()
                    
                    if col_y.button("🔄 Ejecutar Reasignación", key=f"rb_{idx}"):
                        if r_nom and r_ced:
                            # Creamos el historial detallado antes de enviarlo
                            motivo = p.get('Notas', 'No especificado')
                            historial = f"REASIGNADO. Original: {p['Nombre']} | ID: {p['ID']} | Entidad: {p['Entidad']} | Motivo: {motivo}"
                            
                            params = {
                                "action": "update", 
                                "old_id": str(p['ID']).strip(), 
                                "id": str(r_ced).strip(), 
                                "nombre": r_nom, 
                                "entidad": r_ent, 
                                "estado": "RECIBIDO", 
                                "mci": p['mCI'], 
                                "notas": historial
                            }
                            requests.get(SCRIPT_URL, params=params, timeout=15)
                            st.session_state.lista_local = cargar_
