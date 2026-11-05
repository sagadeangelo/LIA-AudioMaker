# Auditoría y plan — 2 de noviembre de 2026

## Base real

Repositorio: `sagadeangelo/LIA-AudioMaker`.
Inspección desde `main` `812e72a33b66357f62d22f0ca9662f2d0c59e490`.
Etiqueta anotada `v0.1.9-mvp`: commit `1b61c92ec6d0b58bdae54807cdd9239a17941503`.
Rama de trabajo: `feat/voice-pronunciation-editor`. Sin push ni despliegue.
La copia antigua 0.1.8 del entorno no se reutilizó ni sobrescribió.

La base usa FastAPI, React/TypeScript/Vite, SQLAlchemy y PostgreSQL en Docker;
SQLite permite pruebas aisladas. `projects` almacena documentos JSON y `jobs`
existía pero los trabajos de exportación aún estaban en memoria.

- `backend/app/main.py`: generación por fragmento, `segments[].audio` como
  referencia activa, `versions[]` como historial, exportación de capítulo.
- `tts_provider.py`: adaptador Kokoro/Azure. `kokoro.py` y `azure.py`: HTTP,
  WAV y normalización PCM16. No se necesitan modelos nuevos para Voice Editor.
- `audio_library.py`: inventario de archivos e historial.
- `book_export.py`: exportación síncrona de libro.
- `book_export_jobs.py`: exportación en hilo con progreso, estado en memoria.
- Almacenamiento: WAV con UUID dentro de `DATA_DIR`, volumen Docker `audio_data`.
- El historial previo conservaba WAV, pero regenerar reemplazaba inmediatamente
  la referencia activa. No había aprobación ni diccionario de pronunciación.
- UI: estudio, casting, biblioteca y exportación; se conserva su CSS real.

## Pruebas de la base

Se ejecutó el código original por separado desde el archivo de respaldo:
21 pruebas backend pasaron y 5 fallaron porque esperaban voces/velocidades de
eSpeak en la API que ya utiliza Kokoro/Azure. Frontend: 11 pruebas y build OK.
Las pruebas antiguas se actualizaron al contrato real y se aislaron del TTS externo
con una fixture PCM explícita. Esto no equivale a probar la calidad de un modelo.

## Plan y estado por fase

1. **Voice Editor: implementación integrada, validación local de voz pendiente.**
   Diccionario, texto alternativo sin editar manuscrito, alcance y vista previa,
   confirmación de lotes, trabajos persistidos, propuestas, comparación,
   aprobación/descarte/restauración y selección aprobada en tres exportadores.
   No requiere tablas nuevas ni migraciones destructivas: campos JSON aditivos
   en `projects.payload` y registros identificados en `jobs.payload`.
2. **Audio Quality: pendiente.** Reutilizar versiones aprobadas para guardar
   propuestas de corrección. Primero fixtures con DC, clipping y clicks conocidos;
   medir pico/RMS, clipping, loudness/true peak con FFmpeg y señales de borde.
   Ninguna detección de «metal» se considerará fiable sin evidencia de audio.
3. **Voice Clone: pendiente.** Investigar fuentes oficiales, licencias y requisitos
   actuales de RVC/alternativas y XTTS antes de elegir. La demostración requiere
   muestra autorizada y el hardware real. No se instaló ningún motor ni modelo.
4. **Sound Effects: pendiente.** Biblioteca privada con licencia/fuente, clips por
   capítulo con posición/ganancia/recorte/fades, premezcla separada y exportación
   reproducible. Ningún efecto insertado automáticamente.

No se iniciaron las cuatro fases simultáneamente. La siguiente validación es
corregir una palabra en un fragmento de prueba con el Kokoro/Azure del usuario,
escuchar antes/después y aprobar/exportar. Después procede Audio Quality.

## Protección y límites del entorno

Antes de editar se creó un archivo completo del código versionado base, verificado
con SHA256 `64384979ba5b2d9eb016f679a95c69f8e9dccb74616458bfc58dde8f2f7deb21`.
El instalador prepara otro respaldo verificable de cada fuente local que reemplaza
y aborta si encuentra modificaciones distintas de la base admitida.

No hay acceso al disco `C:` del usuario, PostgreSQL, volúmenes, novela o exportación
de cuatro horas. Todas las pruebas usaron carpetas temporales y texto inventado.
No se alteraron datos reales, claves, voces privadas, manuscritos ni audios.
Docker no está instalado en este entorno: se verificaron sintaxis YAML y volumen
existente, pero no se ejecutó Compose, una imagen ni PostgreSQL real. No afirmar
compatibilidad Docker ejecutada antes de la comprobación en Windows.
