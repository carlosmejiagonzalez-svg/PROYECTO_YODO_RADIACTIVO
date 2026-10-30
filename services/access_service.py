"""Control de acceso antes de cargar información de pacientes."""
import streamlit as st


def usuario_autorizado(usuario, correos):
    if not isinstance(correos, (list, tuple)):
        return False
    permitidos = {str(c).strip().lower() for c in correos if str(c).strip()}
    return (
        usuario.get('is_logged_in') is True
        and usuario.get('email_verified') is True
        and str(usuario.get('email', '')).strip().lower() in permitidos
    )


def exigir_acceso():
    try:
        correos = st.secrets['access']['allowed_emails']
        auth = st.secrets['auth']
        google = auth['google']
        configurado = (
            isinstance(correos, (list, tuple)) and bool(correos)
            and all(auth.get(k) for k in ('redirect_uri', 'cookie_secret'))
            and all(google.get(k) for k in ('client_id', 'client_secret', 'server_metadata_url'))
        )
    except (KeyError, FileNotFoundError):
        configurado = False
    if not configurado:
        st.error('Acceso no configurado. Solicite al administrador configurar el inicio de sesión y las cuentas autorizadas.')
        st.stop()
    conectado = getattr(st.user, 'is_logged_in', False)
    if not conectado:
        st.title('Acceso a gestión I-131')
        if st.button('Ingresar con Google'):
            st.login('google')
        st.stop()
    if not usuario_autorizado({**dict(st.user), 'is_logged_in': conectado}, correos):
        st.error('Esta cuenta no está autorizada para acceder a los datos.')
        if st.button('Salir'):
            st.logout()
        st.stop()
    if st.sidebar.button('Cerrar sesión'):
        st.session_state.clear()
        st.logout()
        st.stop()
