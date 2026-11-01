# LIA AudioMaker 0.1.4 · Separadores y escenas quitables

Actualización para 0.1.3. Conserva los proyectos, personajes, voces, asignaciones, manuscritos y archivos de audio existentes.

## Instalar

Guardar `LIA_AudioMaker_Escenas_v0.1.4.zip` en la carpeta raíz autorizada y ejecutar:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Expand-Archive -LiteralPath '.\LIA_AudioMaker_Escenas_v0.1.4.zip' -DestinationPath '.' -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\actualizacion_escenas\APLICAR.ps1'
```

El instalador compara hashes normalizados de las versiones conocidas antes de copiar. Si existen cambios no reconocidos, se detiene para no sobrescribirlos. Crea respaldos del código en `backups\escenas-FECHA` y reconstruye el backend. No elimina volúmenes ni modifica `.env`. Bypass afecta solo a ese proceso; no cambia la política global de PowerShell. La ejecución del instalador en Windows debe comprobarse allí; las pruebas de aplicación se realizaron en Linux/Chromium.

Mantener Vite abierto y recargar el navegador. Abrir el proyecto existente. **No es necesario reimportar el libro.** Si se detuvo Vite, ejecutar `npm.cmd run dev` desde `frontend`.

## Puntos como cambio de escena

Las líneas que contienen exclusivamente cinco o más puntos, con o sin espacios, se consideran separadores. También se admiten dos o más signos «…» en una línea. Por ejemplo:

```text
El personaje terminó de leer.
. . . . . . . . . . . . . . . .
Volvió la vista hacia la ventana.
```

El texto posterior inicia otra escena. Los puntos separadores no se convierten en voz. Una frase como «Espera... no salgas» y los tres puntos aislados habituales no se tratan como cambios de escena con esta regla.

En importaciones nuevas, los separadores se conservan en el manuscrito original y se omiten de los fragmentos de producción. En proyectos antiguos, los fragmentos de puntos mantienen sus identificadores y audio histórico si existía, pero pasan a ser registros estructurales quitados de la producción. Sus voces y demás fragmentos no se reescriben.

La actualización detecta esos registros al abrir el proyecto o utilizar su API. El cambio se guarda junto al siguiente guardado del proyecto; «Actualizar escenas» permite guardarlo expresamente y consultar los totales. La conversión es idempotente. No sustituye el análisis literario: marca el corte, sin inferir por qué el personaje estaba leyendo o qué voz debe usar en el texto citado.

## Quitar una escena

1. Seleccionar el capítulo.
2. En «Escena», elegir un número para ver sus fragmentos.
3. Pulsar **Quitar escena**. Sus fragmentos salen del audiolibro, procesamiento y exportación.
4. **Restaurar escena** vuelve a incluir todos los fragmentos de contenido quitados de esa escena, incluidos los que se hubiesen quitado individualmente. Los separadores estructurales nunca se restauran como narración.

Quitar es una exclusión reversible, no un borrado físico. Se conservan orden, texto, hablante, voz, velocidad, color, versiones y referencias de audio. La numeración de escenas no cambia por quitar contenido.

## Quitar un fragmento o varios

- Seleccionar un fragmento y pulsar **Quitar fragmento** en el panel derecho.
- En **Selección múltiple**, marcar los fragmentos y pulsar **Quitar seleccionados**.
- Activar **Mostrar quitados** para verlos con estilo atenuado. Seleccionar uno y pulsar **Restaurar fragmento**.
- En proyectos antiguos, Mostrar quitados también muestra los separadores convertidos; se identifican como tales y no pueden narrarse ni restaurarse como texto hablado.

Cambiar de escena o activar Mostrar quitados limpia las casillas seleccionadas para no actuar sobre una selección oculta. «Seleccionar todos» ahora se limita a la vista actual: el capítulo completo o la escena filtrada, según corresponda. No incluye elementos quitados ni separadores.

## Producción y exportación

- El procesamiento de pendientes omite fragmentos quitados y separadores.
- La reproducción encadenada omite el contenido quitado y respeta la escena visible.
- La exportación WAV/MP3 sigue correspondiendo al **capítulo completo con todas sus escenas incluidas**, aunque la vista esté filtrada por una escena.
- La falta de audio en una escena quitada no bloquea la exportación.
- Un capítulo sin ningún fragmento incluido no puede exportarse.
- Al restaurar contenido con audio ya generado, se recupera su referencia sin regenerarlo. Si no tenía audio, deberá generarse para exportar.
- Las exportaciones descargadas anteriormente son archivos independientes: deben volver a exportarse para reflejar los cambios.

La actualización no añade silencios de duración configurable entre escenas ni un editor manual de cortes; los separadores establecen estructura. El manuscrito original y su archivo fuente no se modifican.

## Validación

- 23 pruebas automatizadas aprobadas: los 19 casos previos más límites del reconocimiento de puntos, migración compatible e idempotente de proyectos antiguos, exclusión/restauración sin pérdida de texto y audio, validación atómica de identificadores y exportación real WAV/MP3 omitiendo contenido quitado. Se comprobó que la duración del WAV coincide con los fragmentos incluidos.
- Compilación TypeScript/Vite aprobada.
- Chromium: conversión de proyecto antiguo sin reimportar; filtro de tres escenas; quitar/restaurar escena completa, fragmento y selección múltiple; ocultar/mostrar quitados; persistencia al recargar; procesamiento TTS y exportación con exclusiones. Sin errores JavaScript.
- Libro completo del propietario: se localizaron 13 líneas separadoras de puntos en el DOCX original. La importación actual conserva los 15 capítulos y no produce fragmentos narrables para esas líneas.

El reconocimiento de nombres y acotaciones sigue siendo heurístico. Se mantienen el límite de importación de 15.000.000 bytes y el catálogo de voz básico existente.
