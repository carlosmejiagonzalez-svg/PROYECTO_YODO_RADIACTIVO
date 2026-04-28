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

# URL de tu Apps Script (Verifica que sea la última implementación)
SCRIPT_URL = "https://script.google.com/macros/library/d/10V9lBuW5fVHdeY-11vTJyWrfEyMmvOzFG34n_gYOAHninBK_Kn3-_GEV/24"
LOGO_PATH = "logo.png"

st.set_page_config(page_title="Nuclear 2000 Ltda", layout="wide")
colombia_tz = pytz.timezone('America/Bogota')
HL_YODO = 8.02 

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(hoja=0):
    try:
        # ttl=0 fuerza a la app a leer el Excel en tiempo real
        df = conn.read(worksheet=hoja, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            return df.to_dict('records')
    except Exception as e:
        st.error(f"Error al cargar hoja {hoja}: {e}")
    return []

def generar_pdf(lista, tipo="PEDIDO"):
    buffer = io.BytesIO()
    orientacion = letter if tipo == "PEDIDO" else landscape(letter)
    doc = SimpleDocTemplate(buffer, pagesize=orientacion, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    elementos = []
    styles = getSampleStyleSheet()
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=80, height=40); img.hAlign = 'LEFT'; elementos.append(img)
    titulo = "PROGRAMACIÓN PEDIDO YODO I131" if tipo == "PEDIDO" else "REPORTE DE TRAZABILIDAD"
    elementos.append(Paragraph(f"<b>{titulo}</b>", ParagraphStyle('T', parent=styles['Title'], fontSize=15, textColor=colors.HexColor("#1A237E"))))
    elementos.append(Spacer(1, 15))
    
    if tipo == "PEDIDO":
        data = [["PACIENTE", "IDENTIFICACIÓN", "ENTIDAD", "FECHA TOMA", "mCi"]]
        for p in lista:
            if p.get('Estado') not in ["CANCELADO", "DECAIMIENTO"]:
                data.append([p['Nombre'], p['ID'], p['Entidad'], p.get('Fecha_Capsula',''), p['mCI']])
        col_widths = [180, 100, 120, 80, 50]
    else:
        data = [["PACIENTE / ID", "ENTIDAD", "mCI", "ESTADO", "F. RECEPCIÓN", "F. ADMIN.", "OBSERVACIONES"]]
        for p in lista:
            data.append([Paragraph(f"<b>{p['Nombre']}</b><br/>{p['ID']}", styles['Normal']), p['Entidad'], p['mCI'], p['Estado'], p.get('Fecha_Recepcion',''), p.get('Fecha_Administracion',''), Paragraph(str(p.get('Notas','')), styles['Normal'])])
        col_widths = [140, 90, 40, 80, 85, 85, 200]

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A237E")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTSIZE', (0, 0), (-1, -1), 8), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

t1, t2, t3, t4 = st.tabs(["👥 Base de Datos", "📅 Programar Semana", "📦 Inventario", "🧮 Calculadora"])

# --- PESTAÑA 1: BASE DE DATOS ---
with t1:
    st.subheader("📝 Registrar Paciente en Espera")
    with st.form("f_maestro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        n = col1.text_input("Nombre").upper()
        i = col1.text_input("Cédula")
        e = col2.text_input("Entidad").upper()
        d = col2.number_input("Dosis mCi", 0.0)
        f = st.date_input("Fecha Tentativa de Toma").strftime("%d/%m/%Y")
        if st.form_submit_button("Guardar en Base de Datos"):
            requests.get(SCRIPT_URL, params={"action":"crear_maestro","nombre":n,"id":i,"entidad":e,"mci":d,"fecha":f})
            st.success(f"Paciente {n} guardado en espera")
            st.cache_data.clear() # Limpia el caché para ver el cambio
            st.rerun()
    
    st.divider()
    lista_base = cargar_datos(hoja=1)
    if lista_base:
        st.write("### Pacientes en Espera (Base de Datos)")
        st.dataframe(pd.DataFrame(lista_base), use_container_width=True)

# --- PESTAÑA 2: PROGRAMACIÓN SEMANAL ---
with t2:
    st.subheader("🚀 Pasar Paciente a la Lista de la Semana")
    lista_base = cargar_datos(hoja=1)
    
    if lista_base:
        df_b = pd.DataFrame(lista_base)
        # El selectbox ahora debería mostrar a MARCELA y CARLOS según tu captura
        opciones = df_b['Nombre'] + " (" + df_b['ID'].astype(str) + ")"
        pac_sel = st.selectbox("Seleccionar paciente de la base de datos", opciones)
        
        if st.button("Confirmar y Mover a Programación"):
            id_extraido = pac_sel.split("(")[1].replace(")","").strip()
            res = requests.get(SCRIPT_URL, params={"action":"programar_desde_base", "id":id_extraido})
            st.success(res.text)
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("No hay pacientes pendientes en la Base de Datos.")
    
    st.divider()
    lista_sem = cargar_datos(hoja=0)
    if lista_sem:
        df_s = pd.DataFrame(lista_sem)
        total = pd.to_numeric(df_s[~df_s['Estado'].isin(['CANCELADO', 'DECAIMIENTO'])]['mCI'], errors='coerce').sum()
        st.metric("Total mCi Pedido", f"{total} mCi")
        
        c_a, c_b = st.columns(2)
        c_a.download_button("📄 IMPRIMIR PEDIDO (PDF)", data=generar_pdf(lista_sem, "PEDIDO"), file_name="pedido.pdf", use_container_width=True)
        if c_b.button("🚨 LIMPIAR LISTA SEMANAL", use_container_width=True):
            requests.post(SCRIPT_URL); st.cache_data.clear(); st.rerun()
        
        for p in lista_sem:
            col_x, col_y = st.columns([4, 1])
            col_x.write(f"**{p['Nombre']}** - {p.get('Fecha_Capsula','')} - {p['mCI']} mCi")
            if col_y.button("Eliminar", key=f"del_{p['ID']}"):
                requests.get(SCRIPT_URL, params={"action":"borrar_paciente", "id":p['ID']})
                st.cache_data.clear(); st.rerun()

# --- PESTAÑA 3: INVENTARIO ---
with t3:
    st.subheader("📦 Trazabilidad e Inventario")
    lista_sem = cargar_datos(hoja=0)
    if lista_sem:
        st.download_button("📑 REPORTE TRAZABILIDAD", data=generar_pdf(lista_sem, "TRAZABILIDAD"), file_name="trazabilidad.pdf", use_container_width=True)
        for idx, p in enumerate(lista_sem):
            with st.expander(f"📍 {p['Nombre']} | {p['Estado']}"):
                col_a, col_b = st.columns(2)
                est = col_a.selectbox("Estado", ["PENDIENTE", "RECIBIDO", "ADMINISTRADA", "CANCELADO", "DECAIMIENTO"], index=0, key=f"s_{idx}")
                f_adm = col_a.date_input("Fecha Admin", key=f"fa_{idx}").strftime("%d/%m/%Y") if est == "ADMINISTRADA" else ""
                obs = col_a.text_area("Notas", value=str(p.get('Notas','')) if str(p.get('Notas',''))!='nan' else "", key=f"o_{idx}")
                if col_a.button("💾 Guardar", key=f"g_{idx}"):
                    requests.get(SCRIPT_URL, params={"action":"update", "old_id":p['ID'], "estado":est, "notas":obs, "fecha_administracion":f_adm})
                    st.cache_data.clear(); st.rerun()
                if p.get('Estado') == "CANCELADO":
                    col_b.info("🔄 Reasignar Dosis")
                    rn, ri = col_b.text_input("Nuevo Nombre", key=f"rn_{idx}"), col_b.text_input("Nueva ID", key=f"ri_{idx}")
                    if col_b.button("Confirmar Traspaso", key=f"tr_{idx}"):
                        requests.get(SCRIPT_URL, params={"action":"reasignar", "nombre":rn, "id":ri, "entidad":p['Entidad'], "mci":p['mCI'], "fecha":p['Fecha_Capsula'], "notas":f"Cedido por {p['Nombre']}"})
                        st.cache_data.clear(); st.rerun()

# --- PESTAÑA 4: CALCULADORA ---
with t4:
    st.header("🧮 Calculadora de Decaimiento")
    ai = st.number_input("Actividad Inicial (mCi)", value=100.0)
    fc, hc = st.date_input("Fecha Calib"), st.time_input("Hora Calib")
    ff, hf = st.date_input("Fecha Calc"), st.time_input("Hora Calc")
    diff = (datetime.combine(ff, hf) - datetime.combine(fc, hc)).total_seconds() / 3600
    if diff >= 0:
        af = ai * math.exp(-math.log(2) * diff / (HL_YODO * 24))
        st.metric("Actividad Final", f"{round(af, 2)} mCi")
