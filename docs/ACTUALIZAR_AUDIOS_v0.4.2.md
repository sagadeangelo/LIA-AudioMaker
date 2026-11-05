# LIA AudioMaker 0.4.2 · Actualizar audios

Actualización incremental sobre Resolver Revisiones 0.4.1.

## Qué cambia

Botón Actualizar audios en Producción / capítulos, junto a los demás controles.
Recarga el proyecto guardado sin usar la copia del navegador, actualiza todas las referencias de audio y fuerza la recarga de las formas de onda. Descarga del reproductor el archivo anterior y carga el activo desde el inicio, sin reproducirlo automáticamente. No genera voces por el mero hecho de recargar.
Cuando se activa una versión nueva desde Estado del libro o Voice Editor, el estudio y el reproductor también se sincronizan automáticamente. Se corrigió el cierre del seguimiento del lote: antes podía interrumpirse la recarga del proyecto al marcar el trabajo como terminado.
Las reproducciones usan siempre el archivo activo del proyecto, incluso al avanzar automáticamente al siguiente fragmento. Se cancelan los avances pendientes al recargar o cambiar de proyecto. Las respuestas antiguas de formas de onda no sustituyen a las nuevas.

## Pronunciación anterior aunque el estado diga listo

Confirmar Conservar audio reparado cierra una revisión, pero no modifica sus bytes. Puede quedar un WAV antiguo si se confirmó por error que ya estaba corregido.
Actualizar audios comprueba además las pronunciaciones guardadas que cambian el texto enviado a TTS, sin dejar que esa confirmación manual oculte un archivo anterior. Si encuentra cambios pendientes, abre Estado del libro en modo Actualizar pronunciaciones guardadas en los audios.
Revisa los fragmentos, confirma la casilla y pulsa Solucionar todo y aplicar al libro. Cuando exista una versión disponible con el mismo texto de origen, voz, velocidad y texto TTS deseado, se podrá reutilizar sin volver a generar. Una propuesta antigua solo por cambios de revisión puede recuperarse si su solicitud coincide; las descartadas o de otro texto no se reutilizan. El resto requiere generar el fragmento completo. Azure consume cuota. Los WAV anteriores se conservan.
Al terminar, el estudio y el reproductor cargarán las referencias nuevas. Escucha de nuevo el primer fragmento y vuelve a exportar el audiolibro completo.

La comprobación no reconoce el sonido por oído. Usa las solicitudes TTS registradas y las reglas guardadas. Una prueba del laboratorio por sí sola no guarda una regla ni cambia los audios del libro. Si la palabra tiene variantes con y sin acento, guarda las reglas correspondientes; las coincidencias siguen siendo palabras completas y distinguen acentos.
El texto visual del manuscrito conserva su ortografía original: la escritura fonética solo se envía al motor de voz.

## Instalación

Copia el ZIP en C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker y extrae en una carpeta nueva.
Ejecuta APLICAR.ps1 con powershell.exe -NoProfile -ExecutionPolicy Bypass -File y su ruta completa.
Después ejecuta ACTUALIZAR_BACKEND.ps1 de esa misma carpeta extraída. Debe indicar Backend listo: 0.4.2.
Mantén el frontend en ejecución y recarga Ctrl+F5; si está detenido, entra en frontend y ejecuta npm.cmd run dev.
Pulsa Actualizar audios. Si abre la comprobación de pronunciación, revisa y aplica los cambios antes de escuchar o exportar de nuevo.
Si hay una asignación sin guardar en el estudio, guárdala antes de recargar.

El instalador valida las fuentes y crea respaldo fuera del proyecto. No toca datos, audios, manuscritos, .env ni volúmenes Docker. El script de backend reconstruye el servicio conservando sus volúmenes. No se hace commit ni push.

## Validación

65 pruebas del backend y 11 pruebas existentes del frontend correctas; compilación TypeScript/Vite correcta.
Prueba Chromium con WAV PCM y texto ficticio: detección de un audio antiguo confirmado manualmente, aplicación explícita de la pronunciación, cambio conjunto de pista/forma de onda/reproductor, recarga de otra activación realizada en el servidor, reproductor detenido al sustituir el archivo, conservación del WAV anterior y ausencia de TTS al recargar.
También se comprobó que una generación normal de Voice Editor actualice el contador de versiones en el estudio y que Aprobar cambie el archivo del reproductor. Sin errores JavaScript.
No se ejecutaron Windows PowerShell, Docker ni las voces reales Azure/Kokoro en este entorno. La comprobación acústica final corresponde a la escucha del usuario.
