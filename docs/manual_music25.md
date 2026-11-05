# Reemplazar música automática · 0.6.25

Requiere interfaz 0.6.24 y backend previo de LIA 0.6.23. Después de instalar y Ctrl+F5: LIA Sound Effects → Música de fondo → elegir escena → Elegir o reemplazar la música de esta escena.

Selecciona una canción de la biblioteca musical del proyecto o pulsa Subir mi música. Las categorías y el tono sugerido no condicionan la elección manual. Si el archivo está en otro proyecto, vuelve a subirlo en este proyecto; no se buscan ni copian archivos ajenos automáticamente. El upload conserva licencia/créditos y queda seleccionado. Pulsa Aplicar mi canción a esta escena.

La acción de aplicación tiene su propio endpoint y no espera la cola de autosalvado de las sugerencias. Comprueba archivo y narración, sustituye solo las pistas musicales de esa escena, conserva efectos y voces, y guarda una marca de elección manual. El balance adicional music_db de esa escena se restablece a cero para usar el volumen elegido sin doble atenuación; los balances de narración y efectos se conservan. Luego la interfaz lee el servidor y comprueba la canción y volumen antes de confirmar.

Una ejecución posterior de un plan automático no añadirá sus músicas nuevas en una escena con una elección manual guardada. La música existente se conserva. Cambiar el proyecto tras exportar un plan invalida su huella: exporta contexto actualizado antes de ejecutar un plan nuevo. No se alteran tokens para eludir comprobaciones. La reanudación de una producción antigua no se mezcla con una edición manual; se bloquean producciones activas, pausadas o interrumpidas.

Para escuchar el cambio genera una preescucha nueva o una nueva exportación con los recursos actuales. El MP3 del piloto generado antes conserva su mezcla anterior. Esta instalación no regenera voces ni audio automáticamente.

Los controles anteriores de clasificación y balance se conservan dentro de Configuración avanzada. Esta corrección crea una ruta explícita de reemplazo manual y verifica su persistencia. El estado exacto del servidor Windows del usuario no ha sido reproducido aquí; no se afirma haber localizado una única causa del fallo previo. Si un recurso falta o no pertenece al proyecto, el endpoint devuelve el motivo en pantalla.

El instalador respalda fuentes conocidas, prueba aislado, compila y reconstruye/reinicia el backend. Ejecutar sin trabajos de producción activos. No cambia proyectos, archivos de audio, credenciales ni iniciador durante la instalación. Inspección visual Windows pendiente.
