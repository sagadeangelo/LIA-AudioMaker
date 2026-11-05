# Planes de producción para revisión (0.6.17)

Requiere exportación 0.6.16. La interfaz se encuentra en Revisión del manuscrito, debajo de Exportar paquete para IA y encima del importador editorial. Carga lia.production-plan versión 1, máximo 5 MB. Muestra errores, advertencias, notas, actuaciones y pistas propuestas. Una casilla explícita permite Guardar plan para revisión si no hay errores. Abrir desde el historial vuelve a comprobar contra el proyecto actual.

## Comprobaciones
Formato estricto y campos prohibidos; identidad del proyecto y tokens de manuscrito/recursos; alcance idéntico al exportado (una escena o todo); escenas y actuaciones repetidas; pertenencia de fragmentos; coincidencia literal de citas; personajes y voces del catálogo; referencias de recursos y duplicados de propuestas. Las dudas del modelo, actuaciones ausentes o de confianza limitada, archivos no disponibles, entradas ambiguas y recursos por conseguir se presentan como advertencias. Si cambian los tokens, se bloquea el guardado: exporta de nuevo para actualizar el plan.

Las citas son comprobadas como subcadenas literales. No se verifica que el modelo interpretó correctamente su significado, ni que la cita de actuación cubra todo el fragmento. Las voces/emociones siguen sin audición o verificación remota. La sincronización exacta por palabras no se calcula todavía.

## Guardado
POST /production-exchange/preview no modifica el proyecto. POST /production-exchange/plans recalcula las comprobaciones bajo bloqueo y exige confirmed=true y el preview_token actual. Guarda solamente production_plans, con copia del JSON, fecha y hash; repetir el mismo JSON reutiliza el registro. No llama motores, no cambia casting, escenas, revisiones o sound_cues, ni genera archivos de audio. Historial y lectura restringidos al proyecto. Los errores estructurales no devuelven el manuscrito completo en la respuesta.

El estado siempre es review_required: guardar no aprueba ni ejecuta. Un plan con advertencias puede guardarse como documento pendiente. Listas vacías de música/efectos conservan lo existente, sin autorización de borrar. No se implementa sustitución/eliminación de cues ni aprobación automática. El siguiente desarrollo es resolución de dudas y acciones explícitas antes de conectar el ejecutor.

El importador editorial detecta lia.production-plan antes de enviarlo y muestra un aviso breve indicando el apartado correcto. El formato lia.editorial-plan sigue funcionando.
