# LIA AudioMaker 0.4.0 · Estado del libro

Actualización incremental para 0.3.1 + los parches EliminarEnEditor y Reparación/Elenco (0.3.1b).

## Instalación

Copia el ZIP directamente a C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker.
Extrae en una carpeta nueva. Desde la raíz del proyecto ejecuta APLICAR.ps1 con powershell.exe -NoProfile -ExecutionPolicy Bypass -File y su ruta completa.
Si el instalador detecta cambios locales incompatibles, se detiene antes de reemplazar archivos. Conserva la salida.
Después ejecuta ACTUALIZAR_BACKEND.ps1 desde la misma carpeta extraída. Espera a ver Backend listo: 0.4.0.
Mantén el frontend en ejecución o ábrelo desde frontend con npm.cmd run dev. Recarga Ctrl+F5.

## Flujo unificado

1. Abre Estado del libro en la barra superior, desde Voice Editor o desde Biblioteca de Audios.
2. Revisa los contadores de todo el proyecto. El filtro por capítulo solo cambia la vista; la aplicación abarca el libro completo.
3. En Propuesta por aplicar, abre cada fragmento y escucha el audio activo y las alternativas. Se preselecciona la propuesta más reciente que coincide con la voz, velocidad y pronunciación guardadas. Si solo hay textos alternativos, debes elegir uno explícitamente.
4. Confirma que revisaste la selección. Pulsa Aplicar cambios revisados al libro.
5. Se reutilizan las propuestas elegidas sin TTS adicional. Se generan los fragmentos sin audio disponible y los audios desactualizados con sus reglas y excepciones por voz. Azure consume cuota. El texto del manuscrito permanece intacto; se regenera el fragmento completo, no solo la palabra.
6. Cada éxito activa un nuevo archivo y conserva el anterior. No se aplica ningún cambio sobre un fragmento que haya cambiado durante el trabajo. El progreso muestra activados e incidencias. Detener termina el fragmento actual; actualizar y repetir solo procesa lo pendiente.
7. Los fragmentos en revisión no se confirman automáticamente: asigna personaje y revisa contenido en el estudio o en reparación individual. Actualiza el estado después.
8. Cuando no haya pendientes detectados, continúa a Exportación completa. Exportar un libro completo requiere que el estado esté resuelto. La vista previa parcial sigue disponible para escuchar los audios activos, que podrían incluir versiones anteriores.

## Qué significa cada estado

- Audio vigente: solicitud TTS registrada coincide con texto, voz y velocidad actuales, o se eligió explícitamente un texto alternativo en este panel.
- Audio histórico conservado: existe un WAV aprobado sin evidencia completa de la solicitud TTS original y no hay una corrección guardada detectada que lo afecte. Se conserva para evitar regenerar innecesariamente toda la novela. No certifica la pronunciación de oído.
- Propuesta por aplicar: hay al menos una propuesta disponible vinculada al estado actual del fragmento. Generarla no significa haberla aprobado.
- Pronunciación o voz por actualizar: el audio aprobado no corresponde a la configuración vigente. También se incluyen los WAV históricos afectados por una regla de pronunciación guardada.
- Sin audio disponible: falta un WAV activo aprobado o su archivo.
- Revisión del contenido pendiente: requiere decisión humana, aunque exista un audio anterior.
- Fuera del audiolibro: fragmento excluido o separador, no entra en aplicación ni en exportación.

Las muestras del laboratorio no son audios de fragmentos y no se incorporan directamente. Primero guarda la regla de pronunciación o su excepción por voz. Las coincidencias del diccionario siguen siendo palabras completas, sin distinguir mayúsculas, y distinguen acentos: Ángelo y Angelo pueden requerir reglas separadas si el manuscrito usa ambas formas.

## Historial y restauración

El historial de trabajos recientes se agrupa en un apartado plegable; no representa el estado vigente. Un lote puede haber generado propuestas que luego se descartaron o sustituyeron. Los contadores se calculan desde el proyecto y los archivos activos.
Restaurar audios anteriores del lote revierte sus activaciones si ningún fragmento cambió después y las versiones anteriores están disponibles. Para fragmentos inicialmente sin audio vuelve a dejarlos sin audio; las nuevas versiones permanecen guardadas. Si hubo cambios posteriores, el lote se rechaza sin restauración parcial: usa las versiones individuales.
Los archivos completos ya descargados no cambian: vuelve a exportar después de aplicar las correcciones.

## Validación y límites

Pruebas aisladas con texto ficticio y WAV PCM de prueba: reutilización de propuestas, todos los capítulos/narrador, excepciones por voz, nuevas generaciones, conflictos, fallos, cancelación/reintento, bloqueo de exportación completa, preservación de archivos y restauración.
Compilación TypeScript/Vite y pruebas existentes del frontend correctas. Flujo Chromium de revisión, aplicación, indicadores, vista móvil y paso a exportación sin errores JavaScript.
No se han ejecutado Docker, PowerShell de Windows ni motores reales Azure/Kokoro en este entorno. La calidad acústica requiere escucha del usuario. No se detectan automáticamente los defectos que no estén representados por una revisión, una propuesta o una configuración guardada.
El instalador solo actualiza fuentes, guarda respaldo y valida huellas; no toca datos, audios, manuscritos, .env ni volúmenes. El script de backend reconstruye el servicio conservando los volúmenes. No se hace commit ni push.
