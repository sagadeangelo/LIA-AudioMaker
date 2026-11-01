# LIA AudioMaker · Actualización de importador 0.1.1

## Instalar en Windows

1. Guardar `LIA_AudioMaker_Importador_v0.1.1.zip` en `C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker`.
2. En PowerShell ejecutar desde esa carpeta:

```powershell
Expand-Archive -LiteralPath '.\LIA_AudioMaker_Importador_v0.1.1.zip' -DestinationPath '.' -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\actualizacion_importador\APLICAR.ps1'
```

Bypass solo se aplica al proceso que ejecuta este script; no cambia la política global de PowerShell. El instalador compara las versiones conocidas antes de reemplazar código y guarda respaldos en `backups\importador-FECHA`. Si detecta modificaciones desconocidas se detiene antes de copiar. Los archivos nuevos y el backend se reconstruyen; `.env`, base de datos, volúmenes y audios existentes se conservan. La aplicación del instalador en un Windows real está pendiente de validación del usuario.

3. Mantener Vite ejecutándose; recargar el navegador.
4. Crear un **nuevo proyecto** (por ejemplo, «Ángelo — importación revisada»).
5. Importar otra vez el DOCX original. Los proyectos ya importados conservan su análisis anterior. Esta actualización no reanaliza ni sobrescribe sus asignaciones o audios.

## Cambios

- Límite de archivo de 15.000.000 bytes, incluido en el backend actualizado.
- Separación de páginas iniciales, dedicatoria, prefacio/prólogo, capítulos y epílogo.
- Unión de capítulo y subtítulo corto en mayúsculas; admite la variación «El SÓTANO» y punto final.
- Propuesta de separación de material final tras grandes espacios de maquetación; estas secciones se marcan «revisar».
- Identificación de etiquetas de hablante en mayúsculas seguidas de dos puntos. Excluye ISBN y otras etiquetas editoriales comunes.
- Unificación de variantes que solo difieren en acento/mayúsculas: ANGELO / ÁNGELO → Ángelo. No se equiparan automáticamente ANDRE / ANDRES ni EL DOCTOR / DR. DITOX.
- El texto visible conserva la etiqueta original. La síntesis utiliza la intervención sin pronunciar «AUGUSTO:».
- Pensamientos o citas entre comillas se marcan para revisión; no se presume que sean diálogo hablado.
- Posibles acotaciones introducidas por comillas curvas se separan como candidatos y exigen revisión. Verbos de habla dentro de intervenciones también activan revisión.
- Posibles continuaciones con interrogación/exclamación o nombre sin dos puntos se marcan para revisión; no se hereda un hablante automáticamente.
- El panel derecho muestra el motivo de revisión y, cuando existe, una sugerencia de hablante. Revisar también el corte de acotaciones antes de guardar la asignación.

## Validación realizada

- 10 pruebas automatizadas aprobadas, incluida generación real eSpeak NG, regeneración y exportación WAV/MP3 de la prueba base.
- Compilación TypeScript/Vite aprobada.
- DOCX del propietario: 13.815.951 bytes; 15 capítulos con sus títulos, 21 secciones totales y 1.247 segmentos tras subdivisión. Todos los 1.257 párrafos originales con texto quedaron representados en encabezados o fragmentos fuente.
- 89 fragmentos con etiqueta explícita de hablante; 142 segmentos marcados para revisión. Estas cifras describen la ejecución de reglas, no una validación semántica de todos los hablantes.
- Prueba de API con el DOCX completo: importación, generación TTS real de una intervención explícita y bloqueo de generación de un fragmento pendiente de revisión.
- Prueba en navegador: selección de capítulo, hablante Augusto reconocido, etiqueta fuente visible, explicación de revisión para pensamientos; sin errores JavaScript.

## Límites actuales

El detector sigue siendo heurístico: no realiza comprensión literaria completa. Las comillas pueden expresar pensamiento, cita, acción o voz; requieren juicio editorial. Las acotaciones sin marcas y las continuaciones sin puntuación identificable pueden permanecer en narración. No todas las formas de guion o nombres mixtos están soportadas. No se infiere que el narrador sea Ángelo solo por estar escrito en primera persona.

Las propuestas «Material final» y «Sobre el autor» dependen de espacios grandes y pistas textuales; revisar su clasificación. No se ha añadido un editor manual de cortes ni una asignación global de voces por personaje. Las modificaciones son compatibles con proyectos antiguos, pero solo las importaciones nuevas utilizan el nuevo análisis.

La comprobación de integridad aquí cubre el texto extraído de párrafos principales DOCX, no garantiza la extracción de texto de imágenes, tablas, notas o cajas flotantes. El documento original no se modifica ni se incluye dentro de este paquete.
