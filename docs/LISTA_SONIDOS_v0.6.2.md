# Lista de sonidos recomendados — 0.6.2

Actualización sobre 0.6.1. Añade **Sonidos recomendados para tu manuscrito** encima del buscador de Freesound.

- La lista toma las recomendaciones de sonido autorizadas en Revisión del manuscrito. Excluye las rechazadas, deshechas y las vinculadas a fragmentos excluidos, eliminados o que ya no contienen la cita. No hace falta volver a analizar un proyecto que ya tiene decisiones guardadas.
- Agrupa las apariciones por nombre de sonido; mar, océano, olas y oleaje comparten un grupo. Otras variantes con nombres distintos se conservan separadas. Muestra las ubicaciones actuales por capítulo y escena.
- Pulsa **Buscar lluvia** (o el sonido que corresponda) para buscarlo en Freesound. Verás un aviso indicando para qué recomendación estás buscando. Puedes ajustar la consulta. Cuando guardes un resultado desde esa búsqueda, quedará vinculado a la recomendación: marca verde, nombre tachado y contador de pendientes reducido.
- Para los sonidos que ya descargaste, abre **Usar sonido que ya tengo para…**, selecciona el recurso y pulsa **Vincular sonido guardado**. También puedes usar el botón **Usar para…** de un resultado que ya esté guardado.
- No se adivina el contenido de los audios a partir del nombre del archivo. La vinculación es explícita para no marcar lluvia como conseguida al descargar un recurso que no corresponda. Una búsqueda general sin recomendación seleccionada guarda el sonido en la biblioteca, pero no completa ningún elemento de la lista.
- **Volver a pendiente** elimina solo la vinculación; conserva el archivo y sus asignaciones de mezcla. Puedes ocultar o mostrar los sonidos conseguidos.
- Las marcas y contadores se guardan en el proyecto y se recuperan al recargar. Si falta el archivo del recurso vinculado, el elemento vuelve a pendiente.
- Un recurso disponible puede cubrir varias recomendaciones si tú lo vinculas a ellas. La lista cuenta tipos de sonido y muestra aparte cuántas apariciones hay; no cuenta cada aparición como otra descarga obligatoria.

La marca significa **recurso disponible en biblioteca**, no **efecto colocado o mezclado**. La colocación sigue haciéndose en el mezclador por escena. No se modifica la narración ni la exportación general del libro.

## Instalación

Aplica APLICAR.ps1 del paquete y luego ACTUALIZAR_BACKEND.ps1. Ruta por defecto: `C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker`. Espera **Backend listo: 0.6.2** y recarga Ctrl+F5. Se conservan .env, la sesión de Freesound, descargas, decisiones y mezclas anteriores. El instalador crea un respaldo y se detiene si encuentra archivos locales distintos de la base 0.6.1.

## Verificación

112 pruebas backend, 18 frontend y compilación TypeScript/Vite correctas. Pruebas de agrupación, vinculación, deshacer, archivo ausente, recursos de otro proyecto y preservación de audios. La prueba de navegador utiliza Freesound simulado; no usa tus credenciales reales.
