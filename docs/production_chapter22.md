# Capítulo I · prueba real preparada · 0.6.22

Este paquete requiere 0.6.21 instalada. Contiene el plan LIA_Produccion_Capitulo_I_Actual_v2.json derivado del contexto completo exportado por el usuario, limitado al capítulo I. Su huella de recursos se calculó con el algoritmo de LIA sobre el catálogo exportado y las pistas de ese capítulo. No modifica la huella del manuscrito.

Alcance: 7 escenas, 113 fragmentos de entrada, 19 divisiones explícitas, 134 partes resultantes. Cada división concatena exactamente el texto original. Se conservan encabezados y etiquetas existentes. Las acotaciones externas pasan al Narrador; la autobiografía permanece con Ángelo.

Se mantienen las 7 músicas ya elegidas y se ajusta su duración al final de cada escena. Se desactivan 3 pistas: golpe genérico duplicado de la bofetada, lluvia que describe otra ciudad retrospectivamente y exclamación de frustración sobre el fragmento donde ahora se separa la acotación del llanto. Los recursos y archivos siguen en biblioteca. Se conserva la bofetada específica y la descarga de cajas. Se añaden un llanto contenido y dos respiraciones breves con recursos existentes. No se escucharon los archivos ni se verificó su disponibilidad en Windows.

ACTUALIZAR.ps1 respalda fuentes, prueba aislado, compila y reinicia backend. No aplica el plan ni produce audios durante la instalación. Tras Ctrl+F5: Analizar manuscrito → Importar plan de producción → seleccionar JSON de este paquete → previsualizar y guardar → Preparar prueba del capítulo → comprobar el resumen y confirmar Producir capítulo automáticamente. No usar Importar análisis editorial externo.

El resumen de producción muestra las pistas por desactivar y motivos antes de confirmar. Se preservan copias de pistas y fragmentos originales dentro del registro de producción, y archivos originales. No se implementa reversión integral con un botón. Las divisiones de 2 a 8 partes admiten volver a la voz del personaje después de una acotación intermedia. Los fragmentos con pistas activas ancladas siguen bloqueando la división; las pistas que el plan desactiva explícitamente no la bloquean.

La aplicación calcula cuántos audios reutilizará o generará y pide confirmar el uso de la API. Los controles de emoción no están garantizados por el motor. Las entradas por citas son aproximadas y necesitan escucha. No editar el proyecto mientras produce. Si el manuscrito, elenco, biblioteca o asignaciones cambiaron después de exportar, la validación bloqueará este plan: no alterar tokens para eludirlo.

El resultado será WAV y MP3 del capítulo, además de créditos. Descargar el paquete no equivale a haber producido el capítulo: la ejecución y escucha reales ocurren en la instalación del usuario.
