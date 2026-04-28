import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math
import io
import os
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# URL de tu Apps Script corregido
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz8FcolZ346Fg3pL_yU1WPpMh4T2NHrR0t0HhAm-0VBDJbrZ7fO78jTKEVcrnfCK54/exec"
LOGO_PATH = "logo.png" 

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
            # Asegurar existencia de columnas para evitar errores de lectura
            for c in ["Nombre", "ID", "Entidad", "Fecha_Capsula", "mCI", "Estado", "Fecha_Recepcion", "Fecha_Administracion", "Notas"]:
                if c not in df.columns: df[c] = ""
            return df.to_dict('records')
    except: pass
    return []

def generar_pdf(lista, tipo="PEDIDO"):
    buffer = io.BytesIO()
    orientacion = letter if tipo == "PEDIDO" else landscape(letter)
    doc = SimpleDocTemplate(buffer, pagesize=orientacion, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    elementos = []
    styles = getSampleStyleSheet()
    
    if os.path.exists(LOGO_PATH):
        try:
            img = Image(LOGO_PATH, width=80, height=40); img.hAlign = 'LEFT'
            elementos.append(img)
        except: pass
    
    titulo_texto = "PROGRAMACIÓN PEDIDO YODO I131" if tipo == "PEDIDO" else "REPORTE DE TRAZABILIDAD Y MOVIMIENTO"
    elementos.append(Paragraph(f"<b>{titulo_texto}</b>", ParagraphStyle('T', parent=styles['Title'], fontSize=15, textColor=colors.HexColor("#1A237E"))))
    elementos.append(Paragraph(f"Fecha Reporte: {datetime.now(colombia_tz).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elementos.append(Spacer(1, 15))
    
    if tipo == "PEDIDO":
        data = [["PACIENTE", "IDENTIFICACIÓN", "ENTIDAD", "FECHA TOMA", "mCi"]]
        for p in lista:
            if p['Estado'] not in ["CANCELADO", "DECAIMIENTO"]:
                f_toma = str(p.get('Fecha_Capsula', '')) if str(p.get('Fecha_Capsula', '')).lower() != 'nan' else ""
                data.append([p['Nombre'], p['ID'], p['Entidad'], f_toma, f"{p['mCI']}"])
        col_widths = [180, 100, 120, 80, 50]
    else:
        data = [["PACIENTE / ID", "ENTIDAD", "mCI", "ESTADO", "F. RECEPCIÓN", "F. ADMIN.", "OBSERVACIONES"]]
        for p in lista:
            f_recep = str(p.get('Fecha_Recepcion', '')) if str(p.get('Fecha_Recepcion', '')).lower() != 'nan' else ""
            f_admin = str(p.get('Fecha_Administracion', '')) if str(p.get('Fecha_Administracion', '')).lower() != 'nan' else ""
            obs = str(p.get('Notas', '')) if str(p.get('Notas', '')).lower() != 'nan' else ""
            data.append([
                Paragraph(f"<b>{p['Nombre']}</b><br/>{p['ID']}", styles['Normal']),
                p['Entidad'], p['mCI'], p['Estado'], f_recep, f_admin, Paragraph(obs, styles['Normal'])
            ])
        col_widths = [140, 90, 40, 80, 85, 85, 200]

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A237E")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTSIZE', (0, 0), (-1, -1), 8), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")])]))
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = cargar_datos()

t1, t2, t3 = st.tabs(["📋 Programación", "📦 Inventario y Trazabilidad", "🧮 Calculadora"])

# --- PESTAÑA 1: PROGRAMACIÓN ---
with t1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            n, i, e = st.text_input("Nombre").upper(), st.text_input("Cédula"), st.text_input("Entidad").upper()
            d = st.number_input("Dosis mCi", 0.0)
            f = st.date_input("Fecha Toma de Cápsula").strftime("%d/%m/%Y")
            if st.form_submit_button("Agregar Paciente"):
                requests.get(SCRIPT_URL, params={"action":"register","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
                st.session_state.lista_local = cargar_datos(); st.rerun()
        st.divider()
        if st.button("🚨 LIMPIAR PANTALLA / RESET", use_container_width=True):
            requests.post(SCRIPT_URL); st.session_state.lista_local = []; st.rerun()
    with c2:
        if st.session_state.lista_local:
            df = pd.DataFrame(st.session_state.lista_local)
            # Solo mostrar los que no están cancelados o en decaimiento
            pacientes_activos = df[~df['Estado'].isin(['CANCELADO', 'DECAIMIENTO'])]
            
            total_mci = pd.to_numeric(pacientes_activos['mCI'], errors='coerce').sum()
            st.metric("Total mCi Pedido", f"{total_mci} mCi")
            
            st.download_button("📄 DESCARGAR PEDIDO", data=generar_pdf(st.session_state.lista_local, "PEDIDO"), file_name="pedido.pdf", use_container_width=True)
            
            st.write("---")
            # Lista con botón de eliminar para cada paciente
            for _, fila in pacientes_activos.iterrows():
                col_nombre, col_btn = st.columns([3, 1])
                col_nombre.write(f"**{fila['Nombre']}** ({fila['mCI']} mCi)")
                
                # Botón de eliminar con una llave única (ID)
                if col_btn.button("🗑️ Borrar", key=f"del_{fila['ID']}"):
                    requests.get(SCRIPT_URL, params={"action": "borrar_paciente", "id": fila['ID']})
                    st.success(f"Eliminado: {fila['Nombre']}")
                    st.session_state.lista_local = cargar_datos() # Recargar datos
                    st.rerun()

# --- PESTAÑA 2: INVENTARIO Y REASIGNACIÓN ---
with t2:
    if st.session_state.lista_local:
        st.download_button("📑 REPORTE TRAZABILIDAD COMPLETO", data=generar_pdf(st.session_state.lista_local, "TRAZABILIDAD"), file_name="trazabilidad.pdf", use_container_width=True)
        for idx, p in enumerate(st.session_state.lista_local):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                col_a, col_b = st.columns(2)
                # Actualización de Estado
                est_list = ["PENDIENTE", "RECIBIDO", "ADMINISTRADA", "CANCELADO", "DECAIMIENTO"]
                est = col_a.selectbox("Estado", est_list, index=est_list.index(p.get('Estado', 'PENDIENTE')), key=f"s_{idx}")
                f_admin_val = col_a.date_input("Fecha Administración", key=f"fa_{idx}").strftime("%d/%m/%Y") if est == "ADMINISTRADA" else ""
                obs = col_a.text_area("Notas / Motivo", value=str(p.get('Notas','')) if str(p.get('Notas',''))!='nan' else "", key=f"o_{idx}")
                
                if col_a.button("💾 Guardar Cambios", key=f"g_{idx}"):
                    requests.get(SCRIPT_URL, params={"action":"update", "old_id":str(p['ID']), "estado":est, "notas":obs, "fecha_administracion":f_admin_val})
                    st.session_state.lista_local = cargar_datos(); st.rerun()

                # Módulo de Reasignación (Si está cancelado)
                if p.get('Estado') == "CANCELADO":
                    col_b.info("🔄 Reasignación de Dosis")
                    rn, ri = col_b.text_input("Nombre Nuevo", key=f"rn_{idx}").upper(), col_b.text_input("ID Nuevo", key=f"ri_{idx}")
                    re, rd = col_b.text_input("Entidad", value=p['Entidad'], key=f"re_{idx}").upper(), col_b.number_input("mCi", value=float(p['mCI']), key=f"rd_{idx}")
                    if col_b.button("Confirmar Traspaso", key=f"tr_{idx}"):
                        h = f"Dosis cedida por {p['Nombre']}. Motivo: {obs}"
                        requests.get(SCRIPT_URL, params={"action":"reasignar", "old_id":str(p['ID']), "nombre":rn, "id":ri, "entidad":re, "mci":rd, "fecha":p['Fecha_Capsula'], "notas":h})
                        st.session_state.lista_local = cargar_datos(); st.rerun()

# --- PESTAÑA 3: CALCULADORA ---
with t3:
    st.header("🧮 Calculadora I-131")
    ai = st.number_input("Actividad Inicial (mCi)", value=100.0)
    fc, hc = st.date_input("Fecha Calibración"), st.time_input("Hora Calibración")
    ff, hf = st.date_input("Fecha Cálculo"), st.time_input("Hora Cálculo")
    dt1, dt2 = datetime.combine(fc, hc), datetime.combine(ff, hf)
    diff = (dt2 - dt1).total_seconds() / 3600
    if diff >= 0:
        af = ai * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Actividad Final", f"{round(af, 2)} mCi")
