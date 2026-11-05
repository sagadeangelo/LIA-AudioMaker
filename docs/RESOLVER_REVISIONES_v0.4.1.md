# LIA AudioMaker 0.4.1 · Resolver revisiones desde Estado del libro

Actualización incremental sobre Estado Unificado 0.4.0.

## Qué corrige

En 0.4.0, el total de pendientes incluía las revisiones de contenido, pero el botón de aplicación solo procesaba propuestas, audio desactualizado y audio faltante. Por eso podían aplicarse 25 cambios y quedar 21 revisiones sin una acción para resolverlas desde el panel.
Ahora la acción Solucionar todo y aplicar al libro también incluye las revisiones. El contador coincide con los fragmentos que se resolverán.

## Uso

1. Abre Estado del libro y pulsa Actualizar estado.
2. Ver todos los pendientes limpia los filtros de capítulo/búsqueda y muestra las decisiones que faltan. Hay hasta 50 fragmentos por página, con navegación. El lote abarca el libro completo.
3. Para revisiones que ya tienen un WAV aprobado, se preselecciona Conservar audio ya reparado y confirmar revisión. Si ya los escuchaste y reparaste, no hay que volver a generarlos.
4. Para revisiones sin audio, elige el personaje en la tarjeta del fragmento. También hay una asignación de personaje en lote. Se usa su voz y velocidad guardadas; no se adivina el hablante. Una selección de perfil puede requerir un nuevo audio si cambia la voz o la pronunciación.
5. Confirma la casilla de revisión y pulsa Solucionar todo y aplicar al libro. Se cerrarán las marcas review/content_review, se aplicarán las propuestas seleccionadas y se generarán los pendientes. La generación Azure consume cuota; conservar un WAV existente no llama a TTS.
6. Espera a que termine. Si no hay pendientes detectados, pulsa Continuar a exportación completa. Los archivos completos descargados antes deben volver a exportarse.

Conservar un audio es una confirmación manual de que su sonido ya es correcto, incluso si la solicitud TTS registrada era anterior a la reparación. No corrige el sonido por sí sola. No uses esta decisión para un audio que todavía necesita un cambio; selecciona su personaje para actualizarlo o edita la pronunciación antes de aplicar.

## Conservación y restauración

El manuscrito, sus textos y los WAV anteriores se conservan. El lote registra las decisiones de revisión, las asignaciones y los audios que activó.
En Historial de trabajos recientes, Restaurar estado anterior del lote recupera tanto las marcas de revisión como las asignaciones y referencias de audio anteriores. Si un fragmento cambió después o falta un WAV previo necesario, se rechaza el lote completo sin una restauración parcial. Los nuevos WAV se conservan.
Los lotes de 0.4.0 y anteriores mantienen su restauración existente.
Un fallo no cierra la revisión afectada. Se muestran las incidencias y el fragmento continúa en pendientes. Los cambios concurrentes se rechazan sin sustituir el audio activo.

## Instalación

Copia el ZIP directamente en C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker y extrae en una carpeta nueva.
Ejecuta APLICAR.ps1 con powershell.exe -NoProfile -ExecutionPolicy Bypass -File y la ruta del instalador.
Después ejecuta ACTUALIZAR_BACKEND.ps1 de esa misma carpeta extraída. Debe indicar Backend listo: 0.4.1.
El frontend puede permanecer en ejecución. Recarga el navegador con Ctrl+F5. Si está detenido: Set-Location frontend; npm.cmd run dev.
El instalador valida las fuentes y guarda respaldo fuera del proyecto. Si encuentra un cambio local incompatible, se detiene antes de reemplazar archivos: comparte la salida para adaptar el parche.
No borra datos, audios, manuscritos, .env ni volúmenes. No hace commit ni push.

## Validación

61 pruebas del backend correctas; compilación TypeScript/Vite correcta.
Prueba Chromium con 21 WAV ya reparados y una revisión adicional sin audio: todos los pendientes visibles, conservación exacta de los 21 WAV sin generación adicional, selección del personaje faltante desde el panel, una sola nueva generación y exportación completa habilitada al terminar. Sin errores JavaScript. Selector comprobado en pantalla móvil.
Pruebas de restauración de marcas, asignación de voz, confirmación manual, invalidez tras cambiar reglas y rechazo de una revisión concurrente.
Se usaron texto ficticio y audios PCM de prueba; no se ejecutaron voces reales Azure/Kokoro, PowerShell de Windows ni Docker en este entorno.
