"""Diagnóstico limitado a encabezados de la copia de prueba, sin datos clínicos."""
import json
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

COPY_ID = '1Ww0lMT88z-sikGSF5BkxX3tChlEp1UDTPniJFUpXmSM'
ACCOUNT = 'robot-medicina@app-medicina-nuclear.iam.gserviceaccount.com'
HEADERS = ['Nombre','ID','Entidad','Fecha_Capsula','mCI','Estado','Fecha_Recepcion','Fecha_Administracion','Notas','Agendado','Reporte_Generado','ID_Tratamiento']


def comprobar_encabezados(credencial_json):
    try:
        info=json.loads(credencial_json)
        if not isinstance(info,dict) or info.get('type')!='service_account' or info.get('client_email')!=ACCOUNT:
            return False, 'El archivo no corresponde a la cuenta de servicio prevista para esta prueba.'
        if info.get('token_uri') != 'https://oauth2.googleapis.com/token':
            return False, 'El archivo tiene una configuración de autenticación inesperada.'
        cred=service_account.Credentials.from_service_account_info(
            info, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
        with AuthorizedSession(cred) as session:
            response=session.get(
                f'https://sheets.googleapis.com/v4/spreadsheets/{COPY_ID}/values/Pacientes!A1:L1',
                timeout=15,
            )
            if response.status_code!=200:
                return False, f'Google no permitió leer los encabezados (HTTP {response.status_code}). Revise la API habilitada y el permiso de Lector de la copia.'
            values=response.json().get('values', [])
        if values != [HEADERS]:
            return False, 'La conexión respondió, pero los encabezados no coinciden con la estructura esperada.'
        return True, 'Conexión privada verificada: se leyeron únicamente los 12 encabezados de la copia de prueba.'
    except Exception:
        # No mostrar excepciones que puedan contener fragmentos de credenciales.
        return False, 'No se pudo verificar la conexión. Compruebe que el JSON esté completo y que la clave siga activa.'
