import json
import unittest
from unittest.mock import patch, MagicMock
from services import connection_probe as probe


class ConnectionProbe(unittest.TestCase):
    def test_rechaza_archivo_o_destino_de_autenticacion_no_previsto(self):
        with patch.object(probe, 'AuthorizedSession') as session:
            for raw in ['no-json', '{}', '[]', json.dumps({'type':'service_account','client_email':probe.ACCOUNT,'token_uri':'https://example.invalid'})]:
                self.assertFalse(probe.comprobar_encabezados(raw)[0])
            session.assert_not_called()

    def test_lectura_limitada_y_errores_no_revelan_clave(self):
        raw=json.dumps({'type':'service_account','client_email':probe.ACCOUNT,'token_uri':'https://oauth2.googleapis.com/token'})
        fake=MagicMock(); response=fake.__enter__.return_value.get.return_value
        response.status_code=200; response.json.return_value={'values':[probe.HEADERS]}
        with patch.object(probe.service_account.Credentials,'from_service_account_info') as credentials, patch.object(probe,'AuthorizedSession',return_value=fake):
            self.assertTrue(probe.comprobar_encabezados(raw)[0])
            self.assertEqual(credentials.call_args.kwargs['scopes'],['https://www.googleapis.com/auth/spreadsheets.readonly'])
            get=fake.__enter__.return_value.get
            self.assertTrue(get.call_args.args[0].endswith('/values/Pacientes!A1:L1'))
            response.status_code=403
            self.assertFalse(probe.comprobar_encabezados(raw)[0])
            response.status_code=200; response.json.side_effect=ValueError('CLAVE_NO_MOSTRAR')
            self.assertNotIn('CLAVE_NO_MOSTRAR',probe.comprobar_encabezados(raw)[1])

if __name__=='__main__': unittest.main()
