# Estado verificado · 1 de noviembre de 2026

## Implementado y probado

- Backend FastAPI operativo y frontend React/TypeScript compilado con Vite.
- Creación y recuperación de proyectos; persistencia SQLite entre procesos.
- TXT y DOCX: extracción probada. EPUB: prueba de orden del spine. PDF: extractor implementado, pendiente validar con un libro real de maquetación compleja.
- Capítulos, separadores de escenas, narración y diálogos mediante reglas conservadoras. Hablante ambiguo queda sin atribución y confianza cero.
- Revisión, cambio de hablante, voz, velocidad y color por segmento.
- TTS real con eSpeak NG 1.51: dos voces diferenciadas; WAV PCM no silencioso.
- Regeneración individual, historial de versiones conservado y resto de audios sin reconstruir.
- Forma de onda calculada a partir de muestras WAV reales.
- Exportación de capítulo WAV y MP3 mediante FFmpeg, con normalización.
- Cuatro pruebas automatizadas pasan, incluida la generación real, exportación en ambos formatos y persistencia en un intérprete nuevo. Una advertencia de compatibilidad futura de TestClient/httpx, sin fallos.
- Compilación TypeScript y empaquetado Vite correctos.

## Verificación visual

Capturas reales en docs: escritorio 1440×1000, 1280×800 y móvil 390×844. El navegador automatizado verifica creación de proyecto, importación del manuscrito, asignación de voces, generación de cinco clips, ondas reales, inicio de reproducción y recuperación al recargar. No sustituye una evaluación auditiva humana de calidad de narración.

## Preparado, sin ejecutar aquí

- Docker Compose con PostgreSQL 16 y backend con eSpeak NG/FFmpeg.
- Scripts PowerShell e instalación en Windows.
- Pruebas con hardware RTX 3050; el motor básico no utiliza GPU.

## Pendiente para completar el alcance original

- Análisis narrativo contextual con IA; relaciones, emociones y fichas persistentes por personaje con pronunciación.
- Separar acotaciones de narrador dentro de un mismo párrafo de diálogo. Actualmente se sintetiza el párrafo entero con una sola voz.
- Proveedor neuronal de calidad editorial y adaptadores externos BYOK; no hay cobros ni conexiones a servicios.
- Worker de generación persistente, cola, reintentos y cancelación. Generación actual síncrona, un solo proceso backend. Tabla jobs reservada pero no utilizada.
- Esquema relacional normalizado y migraciones evolutivas Alembic. Solo migración inicial versionada implementada.
- Editor DAW completo: regla temporal calibrada, cursor sincronizado, clips movibles y divisibles, mezcla de música/ambiente y paneles redimensionables.
- Asignación global de voces por personaje y restauración de versiones desde UI.
- Importación DOCX de tablas/notas y PDF con OCR. Revisión editorial del orden y la integridad de extracción.
- Autenticación, aislamiento por usuario, cuotas, limpieza de exportaciones y despliegue comercial.

Conclusión de aceptación: recorrido básico manuscrito → revisión → dos voces → audio → regeneración → exportación → persistencia demostrado. No se declara completado el MVP integral del prompt maestro ni calidad comercial del audio.
