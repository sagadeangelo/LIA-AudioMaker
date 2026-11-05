# Revisión de manuscritos 0.3.0

## Qué se implementó

Análisis local en segundo plano del proyecto existente, sin reimportar ni reescribir
el manuscrito. Botón **Analizar manuscrito** en las herramientas del estudio.
El informe separado conserva evidencia (hasta ocho extractos por entidad), capítulos,
fragmentos y escenas. Las decisiones se registran en `manuscript_reviews`.

- **Nombres:** elenco guardado, etiquetas de diálogo, atribuciones, tratamientos,
  vocativos y tokens con mayúscula, con variantes de acentos/caso agrupadas para
  revisión. Las categorías «fuerte», «repetido» y «débil» son niveles de evidencia,
  no probabilidades. Un nombre propio no significa necesariamente persona.
  Se pueden buscar Lindsay/Gibrán sin distinguir acentos en el filtro de resultados.
  Los candidatos débiles se ocultan por defecto, salvo búsqueda o activación explícita.
- **Importador:** reconoce etiquetas como `Lindsay:` y `Gibrán:`, además de las
  mayúsculas previas. No trata `Nota:` o frases como `En el bosque:` como hablantes.
  Las líneas de tres o más guiones o subrayados se admiten como separadores.
  Este cambio del importador se aplica a futuras importaciones. Los proyectos
  existentes se inspeccionan con sus textos/fuentes conservados, sin reemplazarlos.
- **Escenas:** inventario de escenas guardadas y propuestas de límites ante
  transiciones explícitas (Horas después, Al día siguiente, INT./EXT., etc.).
  Puedes confirmar comenzar una escena en ese fragmento y deshacer la última
  división. Cambian solo los números de escena, sin cortar texto ni borrar audio.
- **Lugares:** referencias léxicas a ubicaciones y nombres en ciertos contextos
  de lugar. No resuelve todas las casas/ciudades ni desambigua personas y lugares.
- **Emociones y forma de hablar:** indicios como furioso, miedo, sonrió o susurró.
  La etiqueta se vincula al texto, no afirma quién siente la emoción ni modifica
  la actuación del TTS. Se omiten negaciones simples cercanas.
- **Efectos:** candidatos de lluvia, viento, truenos, puertas, vehículos, pasos,
  disparos y teléfono. Se filtran algunas metáforas conocidas, como «lluvia de ideas».
  Recuerdos/hipótesis se señalan para revisar. Confirmar solo guarda una anotación:
  no descarga sonidos, no los inserta y no mezcla pistas. Sound Effects aún no está
  implementado como editor/mezclador.

**Añadir al elenco** crea solo el perfil ausente. No atribuye diálogos ni elige una
voz nueva basándose en género o edad: usa el valor predeterminado existente y
requiere configurar su casting. Un candidato ambiguo puede descartarse. Las
confirmaciones de lugar/emoción/sonido son anotaciones de revisión.

## Límites

Es un analizador de reglas, no un modelo semántico ni NER entrenado. No garantiza
encontrar todos los nombres, escenas, emociones o lugares. Puede confundir una
palabra de inicio de oración con nombre; una sola ocurrencia sin contexto queda
como débil. Los nombres compuestos y apodos necesitan revisión. El silencio no
siempre significa ausencia de sonido ni toda referencia a una acción requiere SFX.
No se promete detección acústica de emociones ni generación automática de efectos.
No se instaló ningún modelo pesado ni se envía el manuscrito a servicios externos.

## API y persistencia

Prefijo `/api/projects/{pid}/analysis`:

- `POST /jobs` → 202; `GET /jobs`; `GET /jobs/{id}`.
- `GET /jobs/{id}/report` → informe y bandera `stale`.
- `POST /review`: job_id, document_token, category=name|scene|place|emotion|sound,
  item_id (UUID de nombre/lugar o índice del resto), decision=confirm|reject.
- `POST /undo-scene` restaura los números de la última división confirmada.

Los trabajos usan la tabla `jobs` con kind=manuscript-analysis. El informe privado
se almacena como UUID.analysis.json dentro de DATA_DIR; no se sube a Git. Un
reinicio marca trabajos pendientes interrumpidos, sin reintentarlos automáticamente.
Un solo proceso backend, como el Compose actual; no es una cola distribuida.
No hay cancelación de la CPU a mitad del análisis. Se puede cerrar y recuperar
el informe al volver a abrir. Las fechas y resultados quedan persistidos.

Si cambian texto, atribuciones, revisiones o escenas, el informe queda obsoleto y
las decisiones nuevas requieren reanalizar. Añadir candidatos al elenco o confirmar
anotaciones no invalida el texto del informe. Confirmar una división sí lo invalida;
reanálisis evita aplicar límites obsoletos. No se reanaliza la novela automáticamente.

## Error al buscar menciones

`Error: Not Found` literal es compatible con una ruta inexistente en un backend
anterior; no significa que un nombre tenga cero coincidencias. La ruta
`GET /api/projects/{pid}/voice-editor/mentions?original=...` está presente en esta
versión, y devuelve 200 con total=0 cuando no encuentra el nombre. El cliente
muestra ahora un mensaje específico cuando FastAPI responde Not Found genérico.

El paquete incluye ACTUALIZAR_BACKEND.ps1: reconstruye solo backend, espera el
arranque y verifica versión 0.3.0 y rutas de menciones/análisis por HTTP. No se
inspeccionó el backend Windows directamente: si la ruta ya existe y el fallo
persiste, se necesitan la versión y los logs reales para diagnosticarlo.

## Verificación

45 pruebas backend, 11 frontend y build TypeScript/Vite. Fixtures incluyen Lindsay,
Gibrán, escenas por guiones/transición, Madrid, ira, lluvia/puerta, negación y
metáfora. Se verificaron aislamiento de proyectos, informe obsoleto, conservación
de texto/audio, confirmación y deshacer escenas. Chromium probó el flujo completo
de revisión, búsqueda, lugares/emoción/sonido y vista móvil sin errores JavaScript.
También se verificó el mensaje de backend desactualizado simulando 404 en la ruta
de menciones. Audio de laboratorio; sin datos o servicios del usuario.

Docker no está disponible en este entorno. Los scripts de Windows se entregan
para ejecución local, sin afirmar que se ejecutaron aquí. Se conservan .env,
volúmenes, manuscritos, WAV y MP3 existentes. Sin migraciones destructivas, commits
ni push.
