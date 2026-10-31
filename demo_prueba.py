"""Demostración con registros ficticios y diagnóstico opcional de encabezados."""
import sys
import types
import uuid
import streamlit as st

st.set_page_config(page_title='Prueba I-131', layout='wide')
config = types.ModuleType('config')
config.SCRIPT_URL = ''
config.SCRIPT_TOKEN = ''
config.COLUMNAS_REQUERIDAS = ['Nombre','ID','Entidad','Fecha_Capsula','mCI','Estado','Fecha_Recepcion','Fecha_Administracion','Notas','ID_Tratamiento']
config.ESTADOS_VALIDOS = ['PENDIENTE','RECIBIDO','ADMINISTRADA','CANCELADO','DECAIMIENTO']
config.LOGO_PATH = 'logo.png'
config.TIMEZONE = 'America/Bogota'
sys.modules['config'] = config
from ui import tabs

if 'lista_local' not in st.session_state:
    st.session_state.lista_local = []

def cargar():
    return st.session_state.lista_local

def registrar(nombre, id_paciente, entidad, mci, fecha):
    cargar().append({'Nombre':nombre,'ID':id_paciente,'Entidad':entidad,'mCI':mci,'Fecha_Capsula':fecha,'Estado':'PENDIENTE AGENDAR','Fecha_Recepcion':'','Fecha_Administracion':'','Notas':'','Agendado':'NO','Reporte_Generado':'NO','ID_Tratamiento':str(uuid.uuid4())})
    return True

def buscar(codigo):
    return next(p for p in cargar() if p['ID_Tratamiento'] == codigo)

def agendar(codigo):
    p=buscar(codigo); p.update(Agendado='SI',Estado='PENDIENTE'); return True

def actualizar(codigo,estado,notas,fecha_administracion='',fecha_recepcion=''):
    p=buscar(codigo); p.update(Estado=estado,Notas=notas)
    if fecha_recepcion: p['Fecha_Recepcion']=fecha_recepcion
    if fecha_administracion: p['Fecha_Administracion']=fecha_administracion
    return True

def reasignar(codigo,nombre,id_paciente,entidad,mci,fecha,notas):
    if mci <= 0: st.error('La actividad debe ser positiva.'); return False
    p=buscar(codigo); p['Estado']='DECAIMIENTO'
    registrar(nombre,id_paciente,entidad,mci,fecha); nuevo=cargar()[-1]; nuevo.update(Agendado='SI',Estado='PENDIENTE',Notas=notas)
    p['Notas']='Reasignado al tratamiento '+nuevo['ID_Tratamiento']; return True

def cerrar(ids):
    for codigo in ids: buscar(codigo)['Reporte_Generado']='SI'
    return True

def reset():
    for p in cargar(): p['Agendado']='NO'
    return True

tabs.cargar_datos=cargar
tabs.registrar_paciente=registrar
tabs.agendar_paciente=agendar
tabs.actualizar_paciente=actualizar
tabs.reasignar_dosis=reasignar
tabs.cerrar_trazabilidad=cerrar
tabs.reset_completo=reset
tabs.borrar_paciente=lambda codigo: False
st.title('☢️ Prueba de gestión I-131')
st.warning('ENTORNO DE PRUEBA: use únicamente datos ficticios. La información se pierde al cerrar la sesión y no se conecta a la hoja real.')
a,b,c=st.tabs(['📋 Programación','📦 Inventario y trazabilidad','🧮 Calculadora'])
with a: tabs.render_programacion()
with b: tabs.render_inventario()
with c: tabs.render_calculadora()

with st.expander('Comprobar conexión privada — solo encabezados'):
    st.caption('Esta comprobación consulta solo la primera fila de la copia de prueba. No importa ni modifica pacientes.')
    if st.button('Verificar conexión privada'):
        try:
            credencial_json = st.secrets['service_account_json']
        except (KeyError, FileNotFoundError):
            st.info('Falta configurar service_account_json en Secrets de esta aplicación de prueba.')
        else:
            from services.connection_probe import comprobar_encabezados
            ok, mensaje = comprobar_encabezados(credencial_json)
            if ok:
                st.success(mensaje)
            else:
                st.error(mensaje)
