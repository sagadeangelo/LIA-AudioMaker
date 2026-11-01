# LIA AudioMaker 0.1.3 · Reparto inicial y selección múltiple

Actualización acumulativa para instalaciones conocidas 0.1.1 o 0.1.2. Incluye el elenco de 0.1.2. No elimina tus proyectos ni requiere reimportar los existentes.

## Instalar

Guarda `LIA_AudioMaker_Flujo_v0.1.3.zip` en la raíz autorizada y ejecuta:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Expand-Archive -LiteralPath '.\LIA_AudioMaker_Flujo_v0.1.3.zip' -DestinationPath '.' -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\actualizacion_flujo\APLICAR.ps1'
```

El instalador valida archivos contra las versiones conocidas antes de copiar, respalda el código en `backups\flujo-FECHA` y reconstruye el backend. Conserva `.env`, base de datos, volúmenes y audios. La política Bypass solo afecta ese proceso de PowerShell. Su ejecución en un Windows real queda pendiente de comprobar por el usuario.

Mantén Vite ejecutándose y recarga el navegador. Si lo cerraste, desde `frontend` ejecuta `npm.cmd run dev`.

## Flujo inicial

1. Crear un proyecto e importar un manuscrito. Aparece un asistente con el número de personajes/roles atribuidos y el narrador separado.
2. Pulsar «Sí, elegir voces», o «Revisar después» para ir al editor.
3. Elegir la voz, velocidad y color de cada perfil. «Escuchar» genera y reproduce una muestra real de esa voz.
4. «Guardar voces y aplicar» guarda el reparto y vincula sus voces a todas las intervenciones con hablante conocido, en todos los capítulos.
5. «Aplicar voces y procesar audio» hace lo anterior y genera los fragmentos pendientes que no requieren revisión editorial, incluida la narración. Muestra progreso y permite detenerse después del fragmento actual.
6. Los diálogos sin hablante y el contenido marcado para revisión permanecen pendientes; no se inventan voces para ellos.

En proyectos existentes, abrir «Configurar voces del libro» para hacer este mismo recorrido sin importar de nuevo. La elección del catálogo se guarda. Aplicar de nuevo el reparto sustituye las configuraciones individuales de las atribuciones conocidas por los valores del perfil; los originales y las versiones históricas de audio se conservan.

## Individual o múltiple

El modo individual y el arrastre de una tarjeta a un fragmento siguen disponibles.

Para trabajar con varios:

1. Pulsar «Selección múltiple». Aparecen casillas tanto en el manuscrito como en los clips; representan la misma selección.
2. Marcar las frases que correspondan a un personaje.
3. «Seleccionar todos» tiene alcance explícito: diálogos/candidatos del capítulo actual, o todos sus fragmentos. No selecciona el libro completo. Se puede limpiar la selección o cambiar de capítulo, lo cual la reinicia.
4. Pulsar el nombre del personaje en el elenco para asignar nombre, voz, velocidad y color a todos los seleccionados. También se puede arrastrar su tarjeta sobre un fragmento seleccionado.
5. Si se arrastra sobre un fragmento no seleccionado, se asigna solo a ese destino.
6. «Deshacer asignación» restaura todo el lote. Si alguno de sus fragmentos fue editado o regenerado después, no se sobrescribe ningún cambio y se informa del conflicto.
7. «Salir de selección múltiple» vuelve al trabajo individual.

Asignar personaje no confirma automáticamente el contenido de pensamientos o acotaciones. Para esos casos sigue existiendo la confirmación editorial individual. El original del manuscrito no cambia.

## Producción de audio

«Procesar audios pendientes» recorre el libro en orden, genera solo fragmentos sin audio y sin revisión pendiente, y guarda cada resultado inmediatamente. Usa respuestas de API compactas para no retransmitir el libro completo en cada frase.

Puede detenerse entre fragmentos; los ya terminados quedan guardados. Un fallo en una frase se contabiliza y se continúa con las demás. Al volver a procesar se intentan las pendientes/fallidas, sin reconstruir las completadas. No es un worker persistente: mantener abierta la pestaña durante el proceso. Si se cierra, los audios completados siguen guardados y se puede continuar después; no se promete que el libro termine en segundo plano.

Cambiar voz, velocidad o hablante deja la versión activa anterior pendiente de regenerar; no elimina los WAV históricos. Cambiar solo el color conserva el audio. La exportación del capítulo sigue requiriendo todos sus fragmentos generados.

## Voces disponibles

Se muestran las seis voces actuales del adaptador eSpeak NG, en español e inglés, con variantes masculinas y femeninas básicas. La etiqueta es una descripción de la variante del motor, no una inferencia sobre el personaje. No existen todavía voces infantiles, de ancianos, actuación emocional o calidad neuronal comercial. Estas capacidades requieren integrar y verificar otro catálogo/motor; no se simulan en esta entrega.

## Validación

- 19 pruebas automatizadas aprobadas: flujo anterior de audio/exportación, elenco, asignación por lote, validación atómica de todo el lote, deshacer más de 30 fragmentos, conflictos sin sobrescritura, aplicación de voces entre capítulos, conservación de fuente, muestras reales y generación con respuesta compacta.
- Compilación TypeScript/Vite aprobada.
- Navegador Chromium: importación con apertura automática del asistente; recuento; elección y escucha de voces; aplicación a todo el libro; selección individual/múltiple; ambos alcances de seleccionar todos; asignación por clic y arrastre a lote; deshacer; procesamiento TTS real; omisión de pendientes editoriales; continuación sin regenerar lo completado; recuperación de configuración. También se comprobó un fallo de generación recuperable, la continuación sin repetir audios correctos y la detención entre solicitudes reales de TTS. Sin errores JavaScript.

## Límites del análisis

El recuento se basa en etiquetas de hablante detectadas y asignaciones existentes, no en una comprensión literaria completa ni en todos los nombres mencionados en prosa. Roles o alias distintos pueden aparecer como perfiles diferentes. Se conserva el análisis heurístico de 0.1.1 y el límite de importación de 15.000.000 bytes. El sistema sigue preparado para uso local y un único proceso de backend.
