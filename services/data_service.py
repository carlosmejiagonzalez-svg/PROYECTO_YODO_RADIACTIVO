import streamlit as st
import requests
import logging
from streamlit_gsheets import GSheetsConnection
from config import SCRIPT_URL, COLUMNAS_REQUERIDAS

logger = logging.getLogger(__name__)

@st.cache_resource
def _get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        conn = _get_connection()
        df = conn.read(ttl=0)
        if df is None or df.empty:
            return []
        df.columns = [str(c).strip() for c in df.columns]
        if "ID" in df.columns:
            df["ID"] = df["ID"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        for col in COLUMNAS_REQUERIDAS:
            if col not in df.columns:
                df[col] = ""
        return df.to_dict("records")
    except Exception as e:
        logger.error("Error cargando datos: %s", e)
        st.error(f"❌ No se pudo cargar los datos: {e}")
        return []

def _get(params, mensaje_exito="", mensaje_error="Error en la operación"):
    if not SCRIPT_URL:
        st.error("⚠️ URL del Apps Script no configurada.")
        return False
    try:
        resp = requests.get(SCRIPT_URL, params=params, timeout=15)
        resp.raise_for_status()
        if mensaje_exito:
            st.success(mensaje_exito)
        return True
    except requests.Timeout:
        st.error("⏱️ La solicitud tardó demasiado. Intenta de nuevo.")
    except requests.HTTPError as e:
        st.error(f"❌ {mensaje_error}: Error HTTP {e.response.status_code}")
    except requests.RequestException as e:
        st.error(f"❌ {mensaje_error}: {e}")
    return False

def registrar_paciente(nombre, id_paciente, entidad, mci, fecha):
    return _get(
        params={"action":"register","nombre":nombre,"id":id_paciente,"entidad":entidad,"mci":mci,"fecha":fecha},
        mensaje_exito=f"✅ Paciente {nombre} registrado correctamente.",
        mensaje_error="No se pudo registrar el paciente",
    )

def borrar_paciente(id_paciente):
    return _get(
        params={"action":"borrar_paciente","id":id_paciente},
        mensaje_exito="🗑️ Paciente eliminado.",
        mensaje_error="No se pudo eliminar el paciente",
    )

def actualizar_paciente(old_id, estado, notas, fecha_administracion=""):
    return _get(
        params={"action":"update","old_id":old_id,"estado":estado,"notas":notas,"fecha_administracion":fecha_administracion},
        mensaje_exito="💾 Cambios guardados.",
        mensaje_error="No se pudo actualizar el registro",
    )

def reasignar_dosis(old_id, nombre, id_nuevo, entidad, mci, fecha, notas):
    return _get(
        params={"action":"reasignar","old_id":old_id,"nombre":nombre,"id":id_nuevo,"entidad":entidad,"mci":mci,"fecha":fecha,"notas":notas},
        mensaje_exito="🔄 Dosis reasignada correctamente.",
        mensaje_error="No se pudo completar la reasignación",
    )

def reset_completo():
    if not SCRIPT_URL:
        st.error("⚠️ URL del Apps Script no configurada.")
        return False
    try:
        resp = requests.post(SCRIPT_URL, json={"confirmar": "BORRAR_TODO"}, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        st.error(f"❌ Error en reset: {e}")
        return False
