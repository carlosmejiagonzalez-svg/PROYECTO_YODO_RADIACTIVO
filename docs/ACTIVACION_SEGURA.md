# Activación coordinada pendiente

Los cambios de la rama `correcciones-pedido-yodo` son una propuesta. No se ha migrado la hoja original, desplegado el nuevo Apps Script ni cambiado la aplicación habitual.

## Hallazgo comprobado el 30 de octubre de 2026

La hoja original tiene un permiso `anyone / writer`: cualquier persona que conozca el enlace puede editarla. La copia de prueba solo muestra al propietario. Los permisos no se han modificado. La primera prioridad es conectar la aplicación a una hoja restringida antes de retirar el acceso por enlace de la hoja original.

## Qué protege esta versión

- `app.py` solicita ingreso con Google y comprueba una lista de correos autorizados y que el correo esté verificado, antes de importar los servicios de datos.
- Sin configuración de acceso, la aplicación se detiene sin cargar pacientes.
- La lectura exige una cuenta de servicio de Google; no acepta la conexión pública como alternativa.
- Las escrituras viajan mediante POST JSON, con una clave compartida entre el servidor de Streamlit y las Propiedades del script. No se envían datos de pacientes ni la clave en parámetros de la URL.
- El Apps Script rechaza solicitudes GET y solicitudes POST sin la clave correcta, incluido el reinicio del agendamiento.
- Una respuesta HTTP correcta no basta: se exige `success: true`.
- La demostración `demo_prueba.py` conserva los registros ficticios en memoria. Su diagnóstico opcional usa una clave de prueba guardada en Secrets exclusivamente para leer `Pacientes!A1:L1` de la copia fijada en el código; no importa ni modifica pacientes. No se deben copiar credenciales de producción a una demo.

Estos controles aún deben validarse con Google y Streamlit reales. No constituyen por sí solos una validación institucional del tratamiento de información clínica.

## Orden de prueba

1. Conservar la aplicación habitual y una copia de seguridad previa a cualquier migración.
2. Usar una hoja aparte con registros exclusivamente ficticios. La copia existente contiene registros copiados de la hoja original; no debe publicarse ni usarse para una demo pública.
3. Configurar una cuenta de servicio de solo lectura y compartirle únicamente la hoja de prueba como lectora. Conservar la hoja restringida. Configurar su JSON en `[connections.gsheets]`, con `type = "service_account"`, la URL de la hoja de prueba en `spreadsheet` y `worksheet = "Pacientes"`.
4. Crear una aplicación de prueba con `app.py` desde esta rama. Configurar Google OIDC para la URL concreta de esa aplicación y su ruta `/oauth2callback`. Mantener la lista de correos autorizados cerrada.
5. Actualizar el Apps Script vinculado a la hoja de prueba con `google_apps_script/Code.gs`. Ejecutar manualmente `migrarIdentificadoresTratamiento` solo allí. El código que ya fue probado antes del 30 de octubre no incluye todavía el nuevo control de clave.
6. Ejecutar manualmente `prepararClaveServicio`. El valor se guarda en Configuración del proyecto > Propiedades del script > `API_TOKEN`, sin imprimirlo en el registro. Copiarlo directamente al campo `apps_script_token` en Secrets de la aplicación de prueba. No pegarlo en chats, GitHub ni capturas. No copiar credenciales de producción a una demo.
7. Publicar una implementación nueva de prueba del Apps Script y copiar su URL `/exec` a `apps_script_url`. Una implementación accesible por URL seguirá rechazando las operaciones sin la clave de servidor. Antes de usar información real, revisar también las cuentas ejecutoras y la administración de esta clave.
8. Probar ingreso con cuenta autorizada y no autorizada, lectura privada, registro, agenda, recepción, administración, reporte y cierre. Comprobar persistencia al cerrar y volver a abrir la aplicación, y dos tratamientos de una misma persona.
9. Comprobar que GET, POST sin clave y POST con clave incorrecta no modifican filas.
10. Solo tras aprobar la prueba, coordinar el respaldo, la migración de la hoja original, la conexión privada, la retirada del permiso `anyone`, la actualización de Apps Script y Streamlit y la desactivación de las implementaciones antiguas que aceptaban escrituras sin clave. Actualizar solo uno de estos componentes interrumpe operaciones; una versión antigua del Apps Script que siga activa conserva sus riesgos anteriores.

## Plantilla de Secrets de Streamlit

Valores de ejemplo; no son credenciales operativas. Además de este bloque se requiere la configuración de la cuenta de servicio de lectura de la hoja de prueba.

```toml
apps_script_url = "URL_DE_LA_IMPLEMENTACION_DE_PRUEBA_EXEC"
apps_script_token = "CLAVE_DEL_SERVICIO_DE_PRUEBA_DE_AL_MENOS_32_CARACTERES"

[access]
allowed_emails = ["CORREO_AUTORIZADO"]

[auth]
redirect_uri = "https://URL_DE_LA_APP_DE_PRUEBA/oauth2callback"
cookie_secret = "SECRETO_ALEATORIO_INDEPENDIENTE_DEL_TOKEN_DEL_SERVICIO"

[auth.google]
client_id = "CLIENT_ID_DE_GOOGLE"
client_secret = "CLIENT_SECRET_DE_GOOGLE"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

## Verificación automatizada disponible

- `python -m unittest discover -s tests -p 'test_*.py'`: autorización por correo verificado, bloqueo sin configuración, no envío sin clave, POST autenticado y rechazo de respuestas erróneas.
- `node tests/test_apps_script.cjs`: servicio de Google simulado con datos ficticios. Comprueba clave, bloqueo de GET, migración repetible, tratamientos independientes, cierre y conservación de filas.
- Estos ensayos no sustituyen las pruebas con OAuth real, la cuenta de servicio ni la implementación HTTP de Google.

Documentación de referencia: https://docs.streamlit.io/develop/api-reference/user/st.login

## Diagnóstico limitado de la conexión privada

En la aplicación de demostración desplegada con `demo_prueba.py`, puede configurarse una clave JSON de la cuenta prevista en un secreto raíz llamado `service_account_json`, como cadena literal TOML entre tres comillas simples. No subir el JSON al repositorio ni compartirlo en conversaciones o capturas. El diagnóstico rechaza archivos de otras cuentas y direcciones de autenticación distintas a la de Google. Solo consulta los encabezados de la copia de prueba y presenta mensajes de resultado sin mostrar credenciales ni registros clínicos. Esta prueba confirma la autenticación de lectura; no confirma OAuth de usuarios ni la conexión de escritura del Apps Script.
