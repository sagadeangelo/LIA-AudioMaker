# LIA Sound Effects — 0.6.0

Requiere LIA AudioMaker 0.5.3. Añade una biblioteca de efectos por proyecto. No requiere volver a importar el libro, volver a analizarlo ni regenerar las voces.

## Configuración local

Las credenciales ya guardadas en el archivo `.env` de la raíz se conservan. Docker Compose ahora transmite al backend:

```
FREESOUND_CLIENT_ID=tu_client_id
FREESOUND_API_KEY=tu_client_secret_o_api_key
FREESOUND_CALLBACK_URL=http://freesound.org/home/app_permissions/permission_granted/
```

No pegues credenciales en el chat ni en archivos del frontend. El panel muestra si están presentes; la búsqueda comprueba que Freesound las acepte. No basta con reiniciar un contenedor antiguo: ejecuta el actualizador que lo reconstruye y recrea con las variables nuevas.

La autorización utiliza el callback registrado en Freesound; no envía un callback alternativo. Conserva el callback manual indicado arriba en la aplicación de Freesound. La variable se conserva por compatibilidad, pero no reemplaza el valor registrado en ese servicio.

## Uso

1. Abre un proyecto y pulsa **LIA Sound Effects** en la barra de producción.
2. Comprueba **Credenciales: configuradas** y busca `ocean waves`, `seagulls`, `footsteps` o `car horn`. La búsqueda se ejecuta al pulsar el botón, no mientras escribes. Se muestran 12 resultados por página y se reutilizan por cinco minutos.
3. Escucha las muestras. Empieza con el filtro **CC0**; el filtro **CC BY** está disponible por separado y requiere atribución.
4. Pulsa **Conectar cuenta para originales** → **Abrir autorización en Freesound**. Inicia sesión y autoriza tu aplicación allí.
5. Copia el código temporal mostrado por Freesound; vuelve a LIA, pégalo en **Código temporal** y pulsa **Completar conexión** antes de diez minutos. Ese código no es tu API Key. Si caduca, inicia otra conexión.
6. Pulsa **Guardar original en biblioteca** en el sonido elegido. LIA descarga el original y guarda una versión WAV PCM estéreo de 48 kHz en el proyecto, con nombre, autor, enlace, licencia, duración y fecha. No conserva una segunda copia sin convertir. Límites por original: 50 MB y diez minutos.
7. Puedes escuchar el WAV desde la biblioteca, incluso tras recargar. Repetir la importación del mismo ID no crea duplicados. **Desconectar de LIA** elimina la sesión local y conserva los sonidos. Para revocar también el permiso remoto usa los ajustes de tu cuenta de Freesound.

## Estado del audiolibro

Este paso prepara los recursos. No asigna sonidos a escenas, no cambia las grabaciones aprobadas y no añade música ni emociones a la voz. Los efectos aún no están incluidos en la exportación del audiolibro. El siguiente módulo debe vincular cada efecto a una escena/fragmento, establecer entrada, duración, volumen y fundidos, y exportar una mezcla conservando la narración original.

Los sonidos se guardan en el volumen de audio y sus metadatos en el proyecto. La eliminación definitiva de un proyecto también recoge sus archivos de efectos, respetando las referencias de otros proyectos. Los tokens OAuth se guardan en el subdirectorio privado del volumen, fuera de las rutas públicas de audio; se renuevan al caducar. La conexión es única para esta instalación local de LIA, compartida por sus proyectos. No es un inicio de sesión multiusuario para publicar en internet.

Las licencias de cada sonido y las condiciones de uso de la API son distintas. El panel excluye CC BY-NC. Para un servicio comercial, consulta las condiciones de la API de Freesound; no se obtiene una autorización comercial por introducir una clave. No se descargan colecciones completas ni se usan estos archivos para entrenar modelos.

## Errores frecuentes

- **Credenciales no disponibles**: comprueba `.env` en la raíz y ejecuta `ACTUALIZAR_BACKEND.ps1`. No compartas el contenido de `.env`.
- **Credencial o sesión rechazada**: revisa la clave local; si el error aparece solo al descargar, desconecta de LIA y conecta de nuevo.
- **Límite de solicitudes**: espera antes de reintentar. No pulses repetidamente.
- **Destino no admitido**: esta versión permite solo HTTPS de Freesound y su CDN. Si el servicio cambia de destino, comparte el mensaje para adaptar la integración.
- **No aparece el botón**: reinicia el servidor frontend si está detenido y recarga con Ctrl+F5.

## Verificación de desarrollo

92 pruebas de backend y 18 de frontend correctas; compilación TypeScript/Vite correcta. Prueba de navegador del flujo búsqueda → conexión manual → guardado → recarga → desconexión, con servicio Freesound simulado. Incluye validación de formato, preservación de narración/ediciones concurrentes, límites de descarga, renovación de sesión, redirecciones sin credenciales entre hosts y eliminación de archivos incompletos. No se utilizaron tus credenciales reales ni se verificó tu instalación Windows desde aquí.

Documentación primaria:
- https://freesound.org/docs/api/authentication.html
- https://freesound.org/docs/api/resources_apiv2.html
- https://freesound.org/help/tos_api/
