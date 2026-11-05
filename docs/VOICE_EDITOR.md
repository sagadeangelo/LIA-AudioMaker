# LIA Voice Editor 0.2.0 — primera fase

## Flujo

1. Selecciona un fragmento y guarda su asignación/voz antes de abrir **LIA Voice
   Editor**. El editor usa el casting guardado, no los cambios aún sin guardar.
2. Escucha el audio actual. Agrega una palabra y una escritura alternativa al
   diccionario. No hay pronunciaciones de Ángelo o Ditóx predefinidas: el usuario
   elige la que funciona al escuchar el motor.
3. Elige solo el fragmento, las coincidencias del capítulo o las del proyecto.
   También puedes reemplazar únicamente el texto enviado al motor para ese
   fragmento, conservando `text`, `source_text` y `project.original`.
4. **Revisar fragmentos afectados** muestra original y texto TTS exacto. Revisa
   cada coincidencia. Confirma el checkbox antes de generar más de una propuesta.
5. **Generar propuesta** crea WAV nuevos. Azure consume la cuota del servicio.
   Los botones de audio permiten comparar sin reemplazar el actual.
6. **Aprobar** activa la propuesta para exportaciones nuevas. **Descartar** la
   marca descartada y conserva el archivo. **Restaurar** vuelve a un audio aprobado
   anterior, incluyendo su voz y velocidad, sin sobrescribir WAV.
7. Revisa todos los fragmentos del lote seleccionándolos en el estudio: cada uno
   requiere aprobación individual. Las propuestas no se aprueban en bloque.

El botón habitual **Regenerar fragmento** abre el editor si ya hay audio activo.
La API antigua también guarda regeneraciones como propuestas cuando hay audio
activo. La generación inicial sin audio sigue siendo la acción explícita de
producción y se registra aprobada. Generar aplica las reglas activas del proyecto.

## Diccionario

CRUD por proyecto: palabra, escritura TTS, idioma español, motor, personaje y
estado activo. Coincidencias literales de palabras completas, sin distinguir
mayúsculas; respeta acentos y evita reemplazos encadenados. Las frases más largas
se resuelven primero. Una regla de personaje prevalece sobre la global para la
misma palabra. El idioma registra la intención del usuario; la voz seleccionada
determina el idioma/acento disponible en el motor. No implementa SSML, IPA ni
fonemas específicos de proveedor.

Los lotes incluyen solo texto modificado por el diccionario, dentro del alcance,
con personaje/contenido revisados y fragmentos incluidos. No incluyen separadores,
fragmentos quitados o pendientes de revisión. Un hash de la vista previa impide
iniciar un lote diferente al revisado si cambia el proyecto o el diccionario.

## Persistencia y concurrencia

`pronunciation_rules` y `voice_editor_history` se añaden a los documentos existentes.
Las versiones nuevas guardan UUID, fragmento, archivo, proveedor, voz, velocidad,
texto TTS, fecha UTC, duración, estado y snapshot de origen. Audios históricos se
adoptan como aprobados al consultar versiones; una fecha/proveedor desconocidos
se muestran como tales, sin inventar metadatos.

Los nuevos trabajos se guardan en la tabla `jobs`, con `kind=voice-editor`.
Un hilo procesa un solo trabajo a la vez sin mantener el lock del proyecto durante
el HTTP TTS. Se conserva cada propuesta al terminar el fragmento. La cancelación
se aplica al terminar la llamada en curso; no aborta una petición Azure ya enviada.
Errores no cambian el audio activo. Un reinicio marca trabajos activos interrumpidos:
no hay reintento automático. Puedes crear un nuevo lote tras revisar lo terminado.

**Usar un solo proceso backend**, como el CMD Docker actual. No es una cola
distribuida ni admite varios workers Uvicorn. La generación antigua y exportación
síncrona conservan sus limitaciones anteriores; los trabajos del editor sí son
asíncronos. La exportación de libro existente sigue usando su propio gestor.

Aprobar una propuesta creada antes de un cambio en voz/texto/revisión del fragmento
responde 409. Regenera tras guardar el cambio. Aprobar otra propuesta incrementa
la revisión: las propuestas hermanas anteriores también quedan protegidas. Un
cambio de diccionario no cambia retroactivamente el texto de una propuesta ya
producida: escucha el texto/audio registrado antes de aprobar.

Capítulo, libro síncrono y libro con progreso resuelven solo `audio` aprobado activo.
Los WAV heredados se aceptan por compatibilidad. No cambian las exportaciones
anteriores ni se elimina ningún audio. Propuestas, audios descartados y archivos
parciales conservados pueden aumentar el espacio usado; no hay borrado automático.

## API (prefijo `/api/projects/{pid}/voice-editor`)

- `GET/POST /rules`; `PUT/DELETE /rules/{id}`;
  `PATCH /rules/{id}?active=true|false`.
- `POST /preview`: `scope=segment|chapter|project`, `segment_id` o `chapter_id`,
  `override_text` opcional solo para un fragmento. Devuelve `targets`, `count` y
  `preview_token`.
- `POST /jobs`: mismos campos, `preview_token`, `confirmed` requerido para lotes.
  Devuelve 202 sin esperar al motor. `GET /jobs` y `GET /jobs/{id}` dan progreso;
  `POST /jobs/{id}/cancel` solicita cancelación.
- `GET /segments/{sid}/versions` devuelve historial y audio activo.
- `POST /segments/{sid}/versions/{vid}/approve|reject|restore`.

No se añadieron dependencias ni cambios en Docker Compose. Las claves existentes
permanecen en `.env`. El servicio sigue ligado a localhost, sin autenticación;
no exponerlo públicamente.

## Verificación ejecutada

```powershell
Set-Location "C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker\backend"
$env:PYTHONPATH = "."
python -m pytest -q
Set-Location "..\frontend"
node --experimental-strip-types --test tests/fragmentFilters.test.mjs tests/selection.test.mjs
npm.cmd run build
```

Resultados del entorno de desarrollo: **34 backend**, **11 frontend**, build
TypeScript/Vite OK. La suite comprueba reglas y precedencia, confirmación,
preview obsoleta, exclusiones, cancelación, error TTS, aislamiento de proyectos,
recuperación, persistencia entre procesos, rechazo de propuestas obsoletas,
restauración y exportadores. Se compararon hashes de todos los WAV previos.
FFmpeg exportó WAV/MP3 reales y el WAV exportado cambió solo tras aprobación.

Un test del adaptador Kokoro usa HTTP real y normalización FFmpeg con un servidor
local que entrega PCM de laboratorio. No ejecuta el modelo Kokoro. Chromium probó
el flujo completo de UI, confirmación de lotes, aprobar/restaurar/descartar y
apertura desde el botón habitual, en escritorio y móvil, sin errores JavaScript.

**Pendiente:** prueba audible con Kokoro/Azure real, revisión humana de la
pronunciación elegida, arranque Docker/PostgreSQL y aplicación en Windows. No se
usaron credenciales Azure, modelos de voz ni datos de la novela.


## 0.2.1 — laboratorio de pronunciación

Antes de guardar una regla puedes seleccionar una voz del catálogo existente,
ajustar su velocidad y escuchar la palabra sola o dentro de una frase corta.
**Escuchar original** envía el texto sin sustitución. **Probar pronunciación**
reemplaza la palabra completa por la escritura del campo Pronunciación para TTS.
Puedes repetir cambiando letras o acentos; cada muestra muestra el texto y la voz
exactos usados, para no confundir una prueba anterior con el texto recién editado.
El personaje determina la voz inicial; cambiar la voz de prueba no cambia el casting.

`POST /voice-editor/auditions` crea un trabajo asíncrono aislado. Comparte el límite
de un trabajo activo con los lotes. Se guardan sus muestras en el almacenamiento
de audio y sus referencias en `jobs`, sin crear versiones de fragmentos, guardar
reglas ni activar audios del libro. Las últimas seis muestras se recuperan al
reabrir el editor. No se generan sonidos automáticamente al escribir o cambiar voz.
Azure solo consume cuota al pulsar uno de los botones de prueba.

La frase admite hasta 1000 caracteres y debe contener la palabra original completa;
si está vacía se prueba solo la palabra. La sustitución no distingue mayúsculas,
respeta acentos y no modifica partes de otras palabras. Las voces se reutilizan
del catálogo de la aplicación, agrupadas por Kokoro y Azure; el filtro Motor limita
las opciones. Las muestras se conservan y ocupan espacio. Las reglas guardadas
siguen aplicándose al personaje y motor elegidos, no a una voz de laboratorio.


Verificación 0.2.1: 36 pruebas backend, 11 frontend y build TypeScript/Vite OK.
Chromium verificó elegir voz, probar dos escrituras con acentos diferentes y
comparar con el original antes de guardar; el proyecto y sus WAV activos no
cambiaron. Pruebas con PCM de laboratorio, pendientes de escucha con el motor
real del usuario. Sin cambios de dependencias, tablas ni volúmenes.


## 0.2.2 — eliminar muestras que no quieras conservar

Cada tarjeta del laboratorio incluye **Eliminar muestra**, con confirmación.
Borra únicamente ese WAV de prueba y conserva un registro de eliminación en el
trabajo; la muestra deja de aparecer al reabrir el editor. No se puede deshacer.
No elimina reglas ni modifica el texto, las voces asignadas o los WAV del libro.

El servidor valida que sea una muestra terminada de ese proyecto, usa una ruta
segura y rechaza archivos referenciados por cualquier proyecto (incluida papelera,
historial y deshacer) o por otro trabajo. No acepta nombres de archivo enviados
por el cliente. Detiene la reproducción antes de borrar; si el archivo está en
uso y el sistema impide borrarlo, informa el error y permite reintentar.
Una intención de eliminación persistida permite terminar tras una interrupción.

`GET /voice-editor/auditions` recupera el historial de pruebas no eliminadas,
sin el límite de las últimas seis muestras. Se cargan los audios al reproducirlos.
`DELETE /voice-editor/auditions/{job_id}` elimina una muestra aislada. La operación
es idempotente; un segundo intento no afecta otros archivos. Las muestras sin
borrar siguen ocupando espacio. La eliminación es explícita, nunca automática.

Verificación: 39 pruebas backend, 11 frontend y build OK. Chromium verificó
cancelar/confirmar la eliminación, conservación de otra muestra, persistencia al
reabrir y continuidad del flujo de edición. Audio PCM de laboratorio; ningún
archivo del usuario fue utilizado en estas pruebas. El aplicador Windows conserva
el respaldo de fuentes y no elimina audios: solo el botón solicitado puede hacerlo.


## 0.2.3 — quiénes dicen un nombre y regla uniforme

En el panel derecho, **Quiénes dicen este nombre**, escribe el nombre y pulsa
**Buscar menciones**. Se buscan palabras completas en `segment.text`, sin distinguir
mayúsculas pero respetando acentos; no se busca el nombre del hablante para decidir
quién lo menciona. Cada aparición se agrupa por hablante, voz realmente guardada
en el fragmento y velocidad. Un hablante puede tener varias combinaciones.
Incluye narrador y muestra sin atribuir, quitados y pendientes con su estado.
Los separadores se omiten. Al desplegar un grupo aparecen capítulo, escena,
número de fragmento, texto y cantidad de menciones. Es un inventario de menciones
del manuscrito actual, no una inferencia de identidad ni un registro de audio oído.

Escribe **Una misma pronunciación para todas las voces**. La prueba conjunta
requiere confirmación, produce una muestra por combinación distinta de voz/velocidad
en fragmentos incluidos y revisados, y usa los adaptadores existentes. Repite una
sola escritura para todas las pruebas, sin cambiar los fragmentos o perfiles.
Azure consume cuota solo al generar. Permite detener después de la muestra actual.
Las muestras quedan en el laboratorio y conservan su botón de eliminación.

**Guardar pronunciación uniforme** requiere otra confirmación. Crea/actualiza una
regla global activa, sin personaje y para todos los motores. Desactiva reglas del
nombre y reglas de frases que lo contengan, para evitar que su prioridad altere la
pronunciación común. Los valores anteriores quedan en `voice_editor_history`.
Una regla específica incompatible no puede volver a activarse mientras la uniforme
siga activa. Una regla uniforme tiene prioridad sobre las reglas de personaje.
El hash de la vista de menciones protege contra cambios concurrentes antes de guardar.

La misma escritura se usará también en futuras generaciones con otras voces.
No garantiza una pronunciación acústica idéntica entre modelos: es necesario
escuchar las muestras con las voces reales. No se cambian manuscrito, casting,
WAV actuales ni versiones aprobadas. Para cambiar audios ya producidos, guarda
la regla, revisa el alcance capítulo/proyecto y genera propuestas; las versiones
solo entran en las exportaciones al aprobarlas.

API: `GET /voice-editor/mentions?original=...` devuelve grupos, ocurrencias, reglas
relacionadas y `snapshot_token`. `PUT /voice-editor/uniform-pronunciation` recibe
`original`, `pronunciation`, `snapshot_token` y `confirmed=true`. Reutiliza JSON
existente; no añade tablas ni dependencias.

Verificación: 41 pruebas backend, 11 frontend, build TypeScript/Vite y Chromium.
La prueba de navegador encontró tres hablantes/tres voces, produjo tres muestras,
guardó una regla uniforme, repitió la búsqueda y verificó que el proyecto conservó
sus audios. Se comprobó vista móvil sin desbordamiento y cero errores JavaScript.
Se usó PCM de laboratorio, no modelos ni manuscritos del usuario.

## 0.3.1 — ajustes por voz e incorporación de audios

**Editar pronunciación · [voz]** abre una ventana pequeña con la voz fija,
pronunciación editable, frase de prueba opcional, reproducción de intentos y
**Guardar ajuste de voz**. También aparece **Editar esta voz** en las tarjetas
producidas por las pruebas conjuntas. El ajuste se guarda en
`pronunciation_voice_overrides` por nombre y voz, con historial anterior/posterior.
Afecta a todos los personajes del proyecto que usan esa voz, cualquiera que sea su
velocidad. No cambia las voces asignadas ni su velocidad. Las demás voces mantienen
la regla general. **Volver a pronunciación global** elimina la excepción, conservando
el registro del cambio. Guardar de nuevo una regla global conserva las excepciones.
Las generaciones normales y las correcciones del editor utilizan esta resolución.

La prueba usa la velocidad del grupo seleccionado. No convierte ni clona voces:
regenera una muestra aislada con el motor real asignado. Las muestras pueden
borrarse desde el laboratorio. Cerrar la ventana no aborta una petición TTS enviada.

### Incorporar en el audio

1. Guarda la regla global y los ajustes individuales deseados.
2. Pulsa **Revisar incorporación**. Muestra los fragmentos completos, voz y texto
   que recibirá TTS. Se limita a los que contienen el nombre buscado.
3. Omite quitados, pendientes de revisión/atribución, archivos faltantes o sin audio
   y versiones cuyo texto/voz/velocidad ya coinciden exactamente con lo guardado.
   Un WAV histórico sin metadatos suficientes se considera desconocido y se propone
   regenerarlo; no se inventa su texto TTS. Una regla sin cambios no fuerza regenerar
   WAV cuya solicitud registrada ya coincide.
4. Confirma el checkbox de regeneración y activación y pulsa **Incorporar en el audio**.
   Esa confirmación autoriza activar las versiones nuevas conforme se completen.
   Azure consume cuota; se regeneran fragmentos completos, no solo el nombre.
5. Sigue el progreso. Cancelar detiene después del fragmento en curso. Los cambios
   terminados quedan activos, los demás conservan su estado anterior. Un nuevo plan
   omite los ya actualizados, permitiendo continuar sin repetirlos.
6. Las nuevas exportaciones usan esas versiones aprobadas activas. Los archivos de
   audiolibros ya exportados no cambian. Para obtener un archivo completo actualizado,
   vuelve a exportar después de terminar el lote.

**No se inserta el WAV de la muestra de una palabra dentro de un diálogo.** Aún no
hay alineación temporal ni edición por fonema; hacerlo podría cortar la entonación
y otras palabras. Se solicita al TTS el fragmento completo con su pronunciación
corregida. Por ello pueden cambiar duración/entonación del resto de ese fragmento.
Los demás fragmentos no se regeneran y los WAV anteriores no se sobrescriben.

Un hash protege el plan antes de empezar. Antes de activar cada resultado se
comprueban revisión, texto, voz, velocidad, audio anterior y reglas actuales. Si
hubo cambios concurrentes, se conserva el activo y queda una propuesta para revisión.
Errores del motor no sustituyen el audio. Cada versión incorporada registra el
trabajo, audio anterior, fecha de aprobación y revisión de activación.

**Restaurar audios anteriores del lote** restaura todas sus activaciones si siguen
intactas, incluso para un lote cancelado parcialmente. La comprobación se hace antes
de cambiar el primer fragmento. Si alguno cambió después, se rechaza la restauración
conjunta y se puede usar el historial individual. Ningún WAV se elimina. La regla
fonética sigue guardada después de restaurar: una generación posterior la utilizará.
Un reinicio marca los trabajos interrumpidos y conserva lo terminado, sin reintento
ni gasto automático. Un solo proceso backend, igual que los otros trabajos locales.

API bajo `/voice-editor`:

- `PUT /voice-pronunciation`: original, pronunciation, voice.
- `DELETE /voice-pronunciation/{override_id}`.
- `GET /incorporation?original=...`: targets, skipped, preview_token.
- `POST /incorporation`: original, preview_token, confirmed=true → 202.
- `GET /jobs/{id}` y `POST /jobs/{id}/cancel` reutilizados.
- `POST /incorporation/{id}/restore`.

Verificación: 49 pruebas backend y 11 frontend, build y flujo Chromium con tres
voces. Se probaron edición individual, incorporación/FFmpeg export/restauración,
plan obsoleto, conflictos durante TTS, omisión de faltantes/ya actualizados,
cancelación parcial y protección ante restauración obsoleta. Los hashes de los
WAV previos se conservaron. Audio de laboratorio, no tus voces/archivos reales.
Sin dependencias nuevas, modelos pesados ni cambios destructivos de tablas.
