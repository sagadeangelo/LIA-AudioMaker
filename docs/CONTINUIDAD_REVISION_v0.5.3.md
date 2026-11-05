# Continuidad de la revisión después de dividir escenas · 0.5.3

Base de interfaz: parche de contadores 0.5.2a. Base de backend: 0.5.2. Corrige el bloqueo que impedía terminar otros rubros después de aceptar posibles cambios de escena.

## Instalación

1. Extrae el ZIP en una carpeta nueva.
2. Ejecuta APLICAR.ps1. Verifica todos los archivos antes de aplicar y crea respaldo de fuentes. Se detiene ante cambios locales incompatibles.
3. Ejecuta ACTUALIZAR_BACKEND.ps1 si el aplicador termina correctamente y espera «Backend listo: 0.5.3».
4. Recarga Ctrl+F5. Abre Analizar manuscrito y selecciona el mismo análisis guardado donde ya hiciste tus revisiones.
5. Abre Emociones y forma de hablar, marca Seleccionar todos los pendientes visibles y autoriza las restantes. No vuelvas a analizar ni importes nuevamente el JSON para resolver un cambio de divisiones.

## Corrección

Confirmar una división cambia la estructura de escenas, pero no el texto que se analizó. Ahora se actualizan las referencias de escenas en las sugerencias y el plan sonoro, sin borrar decisiones ni bloquear los rubros restantes. Tanto la revisión individual como la de lote devuelven el informe actualizado. Deshacer divisiones también recarga la revisión.

Se conservan los identificadores de las escenas del informe original para que sus decisiones previas no se pierdan. Una escena realmente nueva puede requerir una revisión propia, con un identificador estable; esto no reinicia las revisiones de las otras escenas.

## Informes anteriores ya bloqueados

Se comprueba si el historial de divisiones del mismo análisis permite reconstruir exactamente el estado originalmente analizado. Si coincide su huella, el informe se puede seguir usando con las escenas actuales y las autorizaciones guardadas. La recuperación se calcula al abrir el informe; no modifica el archivo original del análisis.

Para los análisis nuevos se guarda además una huella de contenido independiente de los números de escena. Así puede verificarse que solo cambió la distribución de escenas.

## Cambios reales del manuscrito

Se mantiene el bloqueo si cambian texto, fragmentos, orden, título de capítulo, atribución u otros datos usados por el análisis y no se puede probar la equivalencia. No basta con pulsar un botón para forzar la aprobación. «Actualizar revisión guardada» vuelve a consultar el informe y conserva las decisiones; si persiste una diferencia material será necesario otro análisis.

No se modifican voces, velocidades, pronunciaciones, audios activos, versiones WAV ni texto del manuscrito. No hay generación ni mezcla de audio en esta corrección.

## Verificación

82 pruebas backend, 18 frontend y compilación. Prueba en navegador con un informe de formato anterior: división ya aplicada, decisiones previas guardadas, 42 emociones seleccionables que bajan a cero y persistencia tras recargar. Las pruebas incluyen conservación del WAV y de los campos de los fragmentos, reproyección de evidencia por escena, recuperación de informes anteriores y bloqueo ante cambios reales de texto.

Las pruebas usan datos de laboratorio; el estado de tu instalación se comprueba al abrir tu análisis guardado después de actualizar.
