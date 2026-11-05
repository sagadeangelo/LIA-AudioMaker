# Dividir diálogo y acotación (0.6.20)

Requiere interfaz 0.6.19 y backend 0.6.18. Abre el plan guardado en Analizar manuscrito → Importar plan de producción. El apartado Separar diálogo y acotación está debajo de la revisión y antes de las notas. Las sugerencias reconocen cierre de cita seguido del nombre del hablante o una atribución explícita. No son comprensión semántica universal ni ejecutan respuestas en lenguaje natural.

## Uso
Selecciona fragmento, revisa el final literal destinado al Narrador y elige personajes existentes para las dos partes. Previsualizar división comprueba el texto. La confirmación permite Aplicar división. El diálogo conserva el ID original; la acotación recibe uno nuevo. Ambas partes conservan escena y texto exacto, sin audio activo ni versiones antiguas incompatibles. El original íntegro, sus metadatos, versiones y audio quedan en el historial del plan y en el inventario de archivos protegidos.

En Divisiones y audios originales puedes escuchar el audio anterior y generar cada parte con el motor/voz configurados. Usa el endpoint de generación existente, no genera otros fragmentos ni mezcla el libro. Puede consumir la API configurada. Tras generar, escucha las partes y actualiza la preescucha de la escena desde el mezclador. La página principal conserva su estado anterior hasta recargar: al terminar pulsa Ctrl+F5 y vuelve a abrir el proyecto.

## Protecciones
El corte debe ser un sufijo literal, sin reescritura ni partes vacías; concatenar ambas partes debe reproducir cada carácter, incluidos espacios y comillas. No se cambia el manuscrito importado original. Personajes de otro proyecto, fragmentos ajenos al plan y previsualizaciones cambiadas se rechazan. El plan debe haber incluido una cita coincidente del fragmento actual. Se bloquean divisiones si hay pistas vinculadas al fragmento, trabajos activos de proyecto o mezcla activa. No se reasignan automáticamente offsets de efectos.

El token considera el fragmento, personajes, orden del capítulo, corte y revisión del plan. Un mismo fragmento no se divide dos veces mientras su división esté activa. El audio original no se usa como audio de un texto recortado. Se conserva en respaldo, accesible en historial. Deshacer restaura el fragmento completo con su audio solo si las dos partes siguen contiguas e idénticas al estado aplicado y no tienen nuevas pistas. Tras editar o generar se bloquea la restauración automática para proteger trabajo nuevo. Nunca se elimina un archivo de audio al dividir o deshacer.

## Plan desactualizado
Dividir modifica la estructura y por tanto el token del manuscrito. Es normal que el plan anterior aparezca desactualizado. Se conservan decisiones y puedes terminar otras divisiones sugeridas cuyo texto siga coincidiendo con el plan. Al terminar exporta de nuevo para revisar el plan actualizado. No se marcan dudas como resueltas ni se sustituyen tokens a mano.

## Alcance actual
Solo divisiones explícitas diálogo/acotación en candidatos del plan; no corrige automáticamente encabezados ESCENA II ni inventa nuevos personajes o voces. No es todavía el ejecutor integral de producción. Las partes deben confirmarse visualmente antes de generar. Verificación visual en Windows pendiente.
