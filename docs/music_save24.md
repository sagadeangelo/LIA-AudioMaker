# Guardado de música · interfaz 0.6.24

Requiere interfaz 0.6.23. Actualización de frontend; backend sigue en su versión actual y no se reconstruye ni reinicia. La instalación no toca proyectos, música, audios, credenciales ni planes.

Cambios: la selección local no se pierde cuando falla la conservación de la elección pendiente; al pulsar guardar se muestra Guardando música, se espera la cola de peticiones con límite y se envía la selección capturada. Después se consulta el mezclador para comprobar que exista esa canción activa, en esa escena, con ese volumen. Solo entonces se confirma guardado. Los errores del servidor aparecen arriba del formulario, cerca del título. Una respuesta no JSON o una petición bloqueada no deja la interfaz esperando indefinidamente. Si vence el plazo, se informa de que la operación podría haberse guardado y debe actualizarse el estado antes de repetir.

Si el guardado se comprueba pero falla actualizar la vista, se distingue ese caso de un error de guardado. El botón de acción tiene type button para no enviar formularios externos. Se muestra la ganancia de pista más el balance musical de la escena; no equivale a normalización de sonoridad. Un reproductor permite escuchar la pista original seleccionada, sin mezclar ni modificarla.

Uso: Ctrl+F5 → proyecto → LIA Sound Effects → Música de fondo → escena → canción → Guardar música de fondo para la escena. Revisa la confirmación o el motivo concreto. Genera una preescucha nueva para oír cambios. Los MP3/WAV anteriores siguen iguales. No genera voces ni cambia automáticamente volúmenes.

Limitaciones: no se identificó el estado concreto del servidor del usuario, al que no hay acceso directo. Se corrigen esperas y pérdida de selección, y se hace verificable el resultado. Si el backend rechaza por audio pendiente, archivo ausente u otro motivo, ahora se muestra; no se eluden esos controles. Pruebas de peticiones bloqueadas, errores HTTP, respuesta no JSON y comprobación de canción, escena, estado y volumen. Compilación validada. Comprobación visual Windows pendiente.
