# Intercambio de producción: etapa 1 y 2 (0.6.16)

## Revisión del importador existente
`backend/app/editorial_plan.py` admite `lia.editorial-plan`, versión 1, hasta 2 MB: personajes, escenas, emociones y sugerencias sonoras vinculadas mediante citas. Usa `/analysis/editorial/preview` e `/import`, previsualización, token, confirmación y aceptación explícita de coincidencias parciales. No es un ejecutor de casting, TTS o mezcla. Se conserva sin modificar.

## Contrato separado
`backend/app/production_exchange.py` define `lia.production-plan` versión 1 mediante modelos estrictos (campos adicionales prohibidos) y exporta su JSON Schema. La identidad combina project_id, document_token, resources_token y scope_scene_ids. Cada escena tiene decisión pending/sound_design/intentional_silence, actuaciones, efectos, música y dudas. Las ubicaciones son fragmento+cita+before/at/after, no segundos inventados. Recursos ausentes se expresan mediante null y search_request. No se aceptan rutas o comandos como campos.

## Exportación de solo lectura
En Revisión del manuscrito → Preparar producción con una IA externa se exporta todo o una escena. GET `/production-exchange/scenes` lista el alcance. GET `/production-exchange/export?scene_id=...` produce un ZIP con contexto.json, esquema_produccion.json, plantilla_produccion.json, esquema_editorial_actual.json e INSTRUCCIONES_PARA_IA.md. Excluye fragmentos quitados. Texto completo, IDs reales y metadatos por lista permitida; no audio, rutas locales, archivos de proyecto ni credenciales. Copia consistente bajo lock; no genera voces ni asigna recursos. Las voces incluidas son Kokoro conocidas más las compatibles configuradas en el libro: no consulta servicios externos ni asegura disponibilidad o control emocional. No es un catálogo remoto exhaustivo.

Los recursos y niveles existentes dan contexto para evitar duplicados. La biblioteca antigua puede carecer de categorías. Los tokens permiten detectar cambios posteriormente: aún NO hay validador de referencias ni importador/ejecutor de producción. La validación estructural Pydantic no equivale a comprobar citas, referencias, duplicados o confianza del plan contra el proyecto: eso corresponde a la siguiente etapa.

## Uso
Descomprime el ZIP y entrega contexto, esquema e instrucciones al modelo elegido; conserva su respuesta JSON. El paquete comparte texto y metadatos con ese proveedor si el usuario lo sube allí. Para iniciar prueba con una escena. No cargues lia.production-plan en el importador editorial; lo rechazará. Plantilla es pendiente, no producción lista.

## Próxima etapa
Previsualización del JSON nuevo: validar alcance, tokens, referencias/citas y límites, resolver faltantes y dudas; guardar planes revisados sin ejecutar aún. Después conectar generación y mezcla reanudables. No hay llamadas LLM ni cambios automáticos de audio en esta entrega.
