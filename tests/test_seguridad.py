import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
from services.access_service import usuario_autorizado
from services import data_service as data


class Seguridad(unittest.TestCase):
    def test_cuenta_autorizada_y_verificada(self):
        self.assertTrue(usuario_autorizado({'is_logged_in':True,'email_verified':True,'email':'MEDICO@example.com'}, ['medico@example.com']))
        for usuario in [
            {'is_logged_in':False,'email_verified':True,'email':'medico@example.com'},
            {'is_logged_in':True,'email_verified':False,'email':'medico@example.com'},
            {'is_logged_in':True,'email':'medico@example.com'},
            {'is_logged_in':True,'email_verified':True,'email':'otra@example.com'},
        ]:
            self.assertFalse(usuario_autorizado(usuario, ['medico@example.com']))
        self.assertFalse(usuario_autorizado({'is_logged_in':True,'email_verified':True,'email':'medico@example.com'}, 'medico@example.com'))

    def test_sin_configuracion_no_carga_datos(self):
        with patch.object(data, '_get_connection') as connection:
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Acceso no configurado' in e.value for e in app.error))
        connection.assert_not_called()
        self.assertEqual(len(app.text_input),0)

    def test_operaciones_autenticadas_solo_post(self):
        response=Mock(); response.raise_for_status.return_value=None
        with patch.object(data,'SCRIPT_URL','https://example.invalid'), patch.object(data,'SCRIPT_TOKEN','x'*64), patch.object(data.st,'error'), patch.object(data.st,'success'), patch.object(data.requests,'post',return_value=response) as post, patch.object(data.requests,'get') as get:
            for payload, expected in [({'success':True},True),({'success':False,'message':'Rechazado'},False),([],False)]:
                response.json.side_effect=None; response.json.return_value=payload
                self.assertIs(data.agendar_paciente('tratamiento-2'),expected)
            response.json.side_effect=ValueError()
            self.assertFalse(data.agendar_paciente('tratamiento-2'))
            response.json.side_effect=None; response.json.return_value={'success':True}
            self.assertTrue(data.reset_completo())
            for call in post.call_args_list:
                self.assertEqual(call.kwargs['json']['api_token'],'x'*64)
                self.assertNotIn('params',call.kwargs)
            self.assertEqual(post.call_args.kwargs['json']['action'],'reset_agendados')
            get.assert_not_called()

    def test_sin_clave_no_envia_datos(self):
        with patch.object(data,'SCRIPT_URL','https://example.invalid'), patch.object(data,'SCRIPT_TOKEN',''), patch.object(data.st,'error'), patch.object(data.requests,'post') as post:
            self.assertFalse(data.registrar_paciente('PRUEBA','123','PRUEBA',10,'01/11/2026'))
            post.assert_not_called()

    def test_lectura_rechaza_conexion_publica(self):
        data._get_connection.clear()
        with patch.object(data.st, 'secrets', {'connections': {'gsheets': {'spreadsheet':'https://example.invalid'}}}), patch.object(data.st, 'connection') as connection:
            with self.assertRaises(ValueError):
                data._get_connection()
            connection.assert_not_called()

    def test_sin_login_no_carga_datos(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
        app.secrets['access']={'allowed_emails':['medico@example.com']}
        app.secrets['auth']={'redirect_uri':'http://localhost:8501/oauth2callback','cookie_secret':'x'*64,'google':{'client_id':'test','client_secret':'test','server_metadata_url':'https://accounts.google.com/.well-known/openid-configuration'}}
        with patch.object(data, '_get_connection') as connection:
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any(b.label=='Ingresar con Google' for b in app.button))
        connection.assert_not_called()

if __name__=='__main__': unittest.main()
