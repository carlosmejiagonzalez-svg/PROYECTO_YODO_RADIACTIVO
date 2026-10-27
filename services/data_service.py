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
        df["ID_Tratamiento"] = df["ID_Tratamiento"].fillna("").astype(str).str.strip()
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
        try:
            resultado = resp.json()
        except ValueError:
            st.error(f"❌ {mensaje_error}: respuesta inválida del servicio. Compruebe el estado antes de reintentar.")
            return False
        if not isinstance(resultado, dict) or resultado.get("success") is not True:
            st.error(f"❌ {mensaje_error}: {resultado.get('message', 'Respuesta no confirmada') if isinstance(resultado, dict) else 'Respuesta no confirmada'}")
            return False
        if mensaje_exito:
            st.success(mensaje_exito)
        return True
    except requests.Timeout:
        st.error("⏱️ La solicitud tardó demasiado. La operación podría haberse completado; compruebe el estado antes de reintentar.")
    except requests.HTTPError as e:
        st.error(f"❌ {mensaje_error}: Error HTTP {e.response.status_code}")
    except requests.RequestException:
        st.error(f"❌ {mensaje_error}: fallo de conexión. Compruebe el estado antes de reintentar.")
    return False

def registrar_paciente(nombre, id_paciente, entidad, mci, fecha):
    return _get(
        params={"action":"register","nombre":nombre,"id":id_paciente,"entidad":entidad,"mci":mci,"fecha":fecha},
        mensaje_exito=f"✅ Paciente {nombre} registrado correctamente.",
        mensaje_error="No se pudo registrar el paciente",
    )

def borrar_paciente(id_paciente):
    return _get(
        params={"action":"borrar_paciente","id_tratamiento":id_paciente},
        mensaje_exito="🗑️ Paciente eliminado.",
        mensaje_error="No se pudo eliminar el paciente",
    )

def actualizar_paciente(old_id, estado, notas, fecha_administracion="", fecha_recepcion=""):
    return _get(
        params={
            "action": "update",
            "id_tratamiento": old_id,
            "estado": estado,
            "notas": notas,
            "fecha_administracion": fecha_administracion,
            "fecha_recepcion": fecha_recepcion,
        },
        mensaje_exito="💾 Cambios guardados.",
        mensaje_error="No se pudo actualizar el registro",
    )

def reasignar_dosis(old_id, nombre, id_nuevo, entidad, mci, fecha, notas):
    return _get(
        params={"action":"reasignar","id_tratamiento":old_id,"nombre":nombre,"id":id_nuevo,"entidad":entidad,"mci":mci,"fecha":fecha,"notas":notas},
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
        try:
            resultado = resp.json()
        except ValueError:
            st.error("❌ Respuesta inválida del servicio. Compruebe el estado antes de reintentar.")
            return False
        if not isinstance(resultado, dict) or resultado.get("success") is not True:
            st.error(f"❌ No se pudo limpiar el agendamiento: {resultado.get('message', 'Respuesta no confirmada') if isinstance(resultado, dict) else 'Respuesta no confirmada'}")
            return False
        return True
    except requests.RequestException:
        st.error("❌ Error de conexión. Compruebe el estado antes de reintentar.")
        return False

def agendar_paciente(id_paciente):
    return _get(
        params={"action": "agendar", "id_tratamiento": id_paciente},
        mensaje_exito="📅 Paciente agendado para esta semana.",
        mensaje_error="No se pudo agendar el paciente",
    )

def cerrar_trazabilidad(ids):
    ids_str = ",".join(ids)
    return _get(
        params={"action": "cerrar_trazabilidad", "ids": ids_str},
        mensaje_exito="📋 Reporte generado y pacientes cerrados correctamente.",
        mensaje_error="No se pudo cerrar la trazabilidad",
    )

