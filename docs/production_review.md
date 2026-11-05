# Resolución editorial del plan (0.6.18)

En Analizar manuscrito → Importar plan de producción guarda o abre un plan. Aparece Resolver revisión del plan: contador, filtro de pendientes y controles por advertencia. Opciones: Revisado (decisión registrada), Conservar lo existente, Requiere un cambio, Decidir después y Pendiente (reabrir). Las tres primeras requieren una respuesta escrita. Guardar respuesta conserva nota y fecha en el plan. El historial muestra los últimos 100 cambios y conserva todos en el registro.

## Semántica
Una respuesta documenta intención, no modifica el JSON original ni escenas, personajes, voces, música o audio. Conservar no aplica cambios. Requiere un cambio y Decidir después siguen pendientes. Revisado registra que se trató la advertencia, sin verificar técnicamente la capacidad del motor. No usar ese reconocimiento como certificación de emociones. Al completar todo se muestra revisión editorial registrada; execution_available sigue false. No habilita producción automática ni aprueba el plan para ejecutarlo.

## Persistencia y concurrencia
Se guardan decisiones por hash de ruta+mensaje de advertencia, con historial antes/después y revisión incremental. El servidor recalcula advertencias y exige preview_token y review_token actuales bajo lock. Si cambian manuscrito, biblioteca o revisión concurrente, rechaza la respuesta. Las respuestas previas siguen consultables; no se trasladan automáticamente a otro plan. Solo se puede responder una advertencia del plan guardado en ese proyecto. Las discrepancias de alcance o referencias no pueden resolverse simplemente marcándolas revisadas: el plan inválido bloquea respuestas nuevas.

## Prueba recomendada
Abre el plan de la escena 1, responde una duda con tu criterio real, guarda, cierra y vuelve a abrir. Verifica que la respuesta persista. Puedes modificarla desde Todas, incluidas las revisadas; elegir Pendiente la reabre y registra el cambio. No se han cambiado las grabaciones. Las dudas de música requieren escuchar antes de decidir; no se han resuelto por el usuario.

## Próxima etapa
Traducir las decisiones en un plan revisado con acciones explícitas y previsualización de cambios, antes de conectar la ejecución reanudable. Esta versión no divide fragmentos ni cambia fronteras, no selecciona otra música y no regenera voces.
