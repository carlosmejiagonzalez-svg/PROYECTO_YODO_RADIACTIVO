import streamlit as st
import requests
import logging
from streamlit_gsheets import GSheetsConnection
from config import SCRIPT_URL, SCRIPT_TOKEN, COLUMNAS_REQUERIDAS

logger = logging.getLogger(__name__)

@st.cache_resource
def _get_connection():
    if st.secrets['connections']['gsheets'].get('type') != 'service_account':
        raise ValueError('Se requiere conexión privada mediante cuenta de servicio.')
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
        logger.error("Error cargando datos: %s", type(e).__name__)
        st.error("❌ No se pudieron cargar los datos. Revise la configuración de conexión con el administrador.")
        st.stop()
        return []

def _post(params, mensaje_exito="", mensaje_error="Error en la operación"):
    if not SCRIPT_URL or len(SCRIPT_TOKEN) < 32:
        st.error("⚠️ Conexión de escritura no configurada. Se requieren la URL y la clave del servicio.")
        return False
    try:
        resp = requests.post(SCRIPT_URL, json={**params, "api_token": SCRIPT_TOKEN}, timeout=15)
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
    return _post(
        params={"action":"register","nombre":nombre,"id":id_paciente,"entidad":entidad,"mci":mci,"fecha":fecha},
        mensaje_exito=f"✅ Paciente {nombre} registrado correctamente.",
        mensaje_error="No se pudo registrar el paciente",
    )

def borrar_paciente(id_paciente):
    return _post(
        params={"action":"borrar_paciente","id_tratamiento":id_paciente},
        mensaje_exito="🗑️ Paciente eliminado.",
        mensaje_error="No se pudo eliminar el paciente",
    )

def actualizar_paciente(old_id, estado, notas, fecha_administracion="", fecha_recepcion=""):
    return _post(
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
    return _post(
        params={"action":"reasignar","id_tratamiento":old_id,"nombre":nombre,"id":id_nuevo,"entidad":entidad,"mci":mci,"fecha":fecha,"notas":notas},
        mensaje_exito="🔄 Dosis reasignada correctamente.",
        mensaje_error="No se pudo completar la reasignación",
    )

def reset_completo():
    return _post(
        params={"action": "reset_agendados", "confirmar": "BORRAR_TODO"},
        mensaje_exito="Agendamientos limpiados; registros conservados.",
        mensaje_error="No se pudo limpiar el agendamiento",
    )

def agendar_paciente(id_paciente):
    return _post(
        params={"action": "agendar", "id_tratamiento": id_paciente},
        mensaje_exito="📅 Tratamiento agendado para el pedido.",
        mensaje_error="No se pudo agendar el paciente",
    )

def cerrar_trazabilidad(ids):
    ids_str = ",".join(ids)
    return _post(
        params={"action": "cerrar_trazabilidad", "ids": ids_str},
        mensaje_exito="📋 Tratamientos seleccionados marcados como reportados.",
        mensaje_error="No se pudo cerrar la trazabilidad",
    )

