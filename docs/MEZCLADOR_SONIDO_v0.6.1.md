# LIA Sound Effects: mezclador de escenas — 0.6.1

Paquete acumulativo compatible con 0.5.3 y 0.6.0, siempre que los archivos coincidan con esas entregas. Incluye la conexión de Freesound de 0.6.0 y añade colocación y mezcla de sonidos por escena. Conserva proyectos, revisiones, credenciales, voces y grabaciones originales. No requiere GPU ni llamadas TTS para mezclar.

## Primera escena con efectos

1. Aplica el paquete y reconstruye el backend con los dos scripts incluidos. Espera **Backend listo: 0.6.1**. Recarga el frontend con Ctrl+F5.
2. Abre tu proyecto → **LIA Sound Effects**. Si todavía no tienes recursos, busca y guarda un sonido en la biblioteca. Para originales conecta tu cuenta desde el panel con el código temporal de Freesound, como se explica en `FREESOUND_v0.6.0.md`.
3. Baja hasta **Mezclar narración y efectos por escena**. Elige una escena. Todas sus voces deben tener un audio aprobado para generar la prueba; el panel indica cuántos faltan. Puedes preparar asignaciones antes, pero los tiempos solo son definitivos con las voces listas.
4. Elige el sonido y el **fragmento de entrada**. El **retraso** se mide en segundos desde el inicio de ese fragmento, no desde el capítulo ni desde el libro. Debe estar dentro de la duración del fragmento.
5. Ajusta el recorte inicial del sonido, su duración, el volumen y los fundidos. Cero en un fundido significa sin fundido. La duración incluye ambos fundidos; su suma no puede superarla.
6. Activa **Repetir** si necesitas que un sonido corto dure más. Se repite desde el punto elegido por **Recortar inicio**, y se detiene al completar la duración indicada.
7. Pulsa **Añadir efecto**. Puedes añadir más, editarlos, desactivarlos o quitarlos. Quitar una asignación conserva el sonido en la biblioteca.
8. Pulsa **Generar mezcla de prueba**. Espera el estado **Lista**. Puedes cerrar el panel durante el proceso y volver después. Si el backend se reinicia durante la mezcla, se registra el error y puedes generar otra.
9. Escucha la mezcla y descarga **WAV** y **créditos de efectos**. Son archivos nuevos y separados de los audios aprobados. Cada generación crea una versión; no actualiza las anteriores.

### Ejemplo de colocación

Si el segundo fragmento de una escena comienza en el segundo 12 y pones un retraso de 1.5 segundos, el efecto empieza en el segundo 13.5 de esa escena. Un ambiente de olas puede comenzar en el primer fragmento con retraso cero; un claxon puede empezar en otro fragmento. Para usar el mismo sonido en varios momentos añade varias asignaciones.

Empieza con −18 dB para ambientes y ajusta escuchando junto a la narración. El motor suma los efectos sin aumentar el nivel de voz y limita los picos a aproximadamente 0.95 de la escala digital. No aplica atenuación automática de ambientes al hablar ni certifica sonoridad ACX/Audible.

## Qué queda guardado

- Asignaciones vinculadas al ID del fragmento, con recorte, retraso, duración, dB, fundidos, repetición y activación.
- Mezclas WAV PCM estéreo de 48 kHz independientes, con fecha, estado y créditos de los sonidos usados en esa versión.
- Una marca de versión anterior cuando cambian la narración, el audio aprobado, los sonidos o las asignaciones de esa escena. El archivo anterior sigue disponible; genera otro para reflejar los cambios.

Una asignación sigue a su fragmento si cambian las divisiones de escena. Si excluyes o eliminas el fragmento, se muestra como asignación sin fragmento y no participa en las mezclas. Los archivos de mezcla se recogen también al eliminar definitivamente el proyecto. Se pueden eliminar versiones de prueba desde el panel sin borrar la narración ni los recursos.

## Alcance y límites de esta entrega

- Mezcla una escena completa; no omite fragmentos sin audio ni usa versiones propuestas sin aprobar.
- Concatena la narración sin introducir pausas adicionales; el retraso se calcula sobre esos audios actuales. El efecto no puede rebasar el final de la escena.
- Hasta 30 minutos y 200 fragmentos por escena, 16 efectos activos por escena, 500 asignaciones por proyecto y 20 versiones guardadas por proyecto. Elimina versiones anteriores si llegas al límite.
- Una mezcla en proceso por instalación, con estado persistente. Ajustes posteriores no alteran una mezcla en curso: se conserva su configuración al iniciarla.
- La selección y colocación son manuales. Autorizar sugerencias editoriales no descarga ni coloca automáticamente sonidos.
- **La exportación general del libro todavía contiene únicamente la narración.** Estas mezclas se escuchan y descargan desde LIA Sound Effects; no se insertan automáticamente en capítulos, MP3 o el libro completo.
- No modifica motores de voz ni añade emociones TTS. No cambia los archivos originales de la narración ni de la biblioteca.

## Comprobaciones de desarrollo

106 pruebas backend correctas y 18 frontend; compilación TypeScript/Vite correcta. Se probaron archivos reales con FFmpeg: entrada al segundo indicado sobre fragmentos con distintas frecuencias de muestreo, duración final, fundidos cero y positivos, repetición, limitación de picos, preservación de originales y versiones anteriores, permisos de proyecto, errores y recuperación tras reinicio. La prueba de navegador cubre alta y edición de asignaciones, generación real, reproducción, descarga WAV/créditos, recarga y marca de mezcla anterior.

No se usaron credenciales reales de Freesound ni se comprobó tu instalación Windows desde aquí. No necesitas compartir tu `.env` para instalar el paquete.
