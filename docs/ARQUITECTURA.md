# Arquitectura inicial y decisiones

React consume la API `/api` mediante el proxy Vite. FastAPI almacena proyectos en SQLAlchemy. El modo local usa SQLite y Compose usa PostgreSQL. La primera migración idempotente registra versión 1 y crea tablas `projects`, `jobs`, `schema_versions`. Los capítulos y segmentos se almacenan como documentos JSON por proyecto, no como tablas normalizadas: es una decisión temporal y explícita.

Cada segmento mantiene identificador, escena, texto, hablante, confianza de detección, revisión, voz, velocidad, color, audio activo y versiones. El original extraído se guarda separado y no se edita. Los bytes originales del archivo importado se conservan con un identificador interno, junto con el nombre fuente en los metadatos; deben respaldarse junto al audio y la base de datos. El extractor DOCX solo admite párrafos principales; tablas, notas y cajas de texto requieren trabajo adicional. PDF puede tener orden de lectura incorrecto por su maquetación y requiere revisión editorial. EPUB sigue el spine; no procesa DRM.

El adaptador actual es eSpeak NG mediante subprocess sin shell; acepta texto por stdin y genera WAV. Se usa una voz sintética básica, no un modelo neuronal de producción. Referencia de opciones: https://github.com/espeak-ng/espeak-ng/blob/master/src/espeak-ng.1.ronn . FFmpeg concatena en orden editorial y normaliza a -19 LUFS, -2 dBTP. No se certifica cumplimiento de plataformas comerciales.

La generación actual es síncrona y bloquea las mutaciones mediante un lock de proceso. Ejecutar un único worker. La tabla jobs es reserva de esquema; no existe todavía worker persistente, reintentos ni recuperación de trabajos. Las exportaciones generan nuevos archivos: limpieza automática y cuotas pendientes. No desplegar para múltiples usuarios.

La vista central es una lista de clips con ondas reales, no una DAW con posiciones temporales editables. El zoom amplía horizontalmente el contenedor. No existen corte, arrastre, mezcla ni pistas de música/ambiente todavía. Esto evita confundir diseño inicial con editor multipista completo.

Próximas migraciones: tablas normalizadas de libros/capítulos/escenas/personajes/voces/segmentos, fichas de personaje y pronunciación; jobs transaccionales, migraciones Alembic y adaptadores TTS/BYOK por capacidades. El análisis contextual de relaciones, emoción y atribuciones sigue pendiente.
