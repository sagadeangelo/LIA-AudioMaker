# Lector de manuscrito y plan por escena · 0.5.0

## Instalación Windows (base 0.4.2)

1. Extrae el paquete en una carpeta nueva.
2. Ejecuta APLICAR.ps1. Verifica los archivos antes de escribir, conserva respaldo y se detiene si detecta cambios locales incompatibles.
3. Si termina correctamente, ejecuta ACTUALIZAR_BACKEND.ps1.
4. Espera «Backend listo: 0.5.0». Recarga Ctrl+F5 y abre Analizar manuscrito → Volver a analizar.

## Cambios

- Plan por escena: personajes mencionados o atribuidos, lugares posibles, emociones, ambientes continuos y efectos puntuales.
- Indicios de mar/oleaje, gaviotas, autos pasando, claxon, tráfico, lluvia, viento, río, aves, grillos, ladridos, puertas, pasos, disparos, teléfono y motor con acción explícita.
- Contexto por oración: separa recuerdos, hipótesis y objetos silenciosos; filtra algunas negaciones y metáforas. Son heurísticas, no comprensión semántica completa.
- Nombres compuestos en atribuciones antes y después del verbo, además del lector existente. Se muestran también candidatos débiles por defecto para que no queden ocultos.
- Evidencia en todos los fragmentos detectados, sin el anterior límite de ocho ejemplos por candidato.
- Confirmar/descartar sonido desde el plan. Decisiones conservadas en el historial del proyecto. Los fragmentos excluidos no aportan sonidos al plan de exportación.
- Más transiciones explícitas de escena. Cada división sigue requiriendo confirmación y puede deshacerse.

## Alcance real

Esta entrega analiza y guarda un plan; NO incluye biblioteca de efectos, generación, mezcla, sincronización temporal ni cambios en WAV o exportaciones. No propaga el ambiente de una escena a otra. Los personajes del plan son menciones/atribuciones detectadas, no una garantía de presencia física.

No garantiza identificar todos los nombres, lugares, escenas o sonidos. No usa un modelo semántico. La negación compleja, ironía, recuerdos extensos y nombres ambiguos requieren revisión. Reanaliza tras editar el manuscrito. Las decisiones de informes anteriores permanecen en el historial; las sugerencias de un análisis nuevo requieren nueva revisión.

## Siguiente etapa

Usar los sonidos confirmados para seleccionar archivos con licencia adecuada, ajustar duración/volumen/fundidos y escuchar una mezcla previa antes de incorporarla al audiolibro.

## Verificación

69 pruebas backend y compilación frontend. La prueba de interfaz se realiza con manuscrito de laboratorio; no comprueba el manuscrito real del usuario ni su instalación Windows.
