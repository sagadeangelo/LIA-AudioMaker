# LIA AudioMaker · Corrección coherente de selección 0.1.7

Compatible con las interfaces 0.1.5 y 0.1.6. Solo modifica las partes necesarias de `frontend/src/main.tsx`; conserva los cambios ajenos al selector. No cambia el backend ni los datos.

## Inconsistencia corregida

Anteriormente se mostraban todas las filas con casillas habilitadas, incluso en modo «Diálogos y candidatos». Las casillas individuales podían marcar narración, mientras que «Seleccionar todos» aplicaba el filtro de candidatos. Era posible marcar filas individualmente y tener a la vez cero elementos elegibles para el selector general.

Ahora el modo activo filtra la lista mostrada en ambos paneles:

- **Diálogos y candidatos de la vista:** muestra solo esos elementos. «Seleccionar todos» marca todas sus casillas de una vez.
- **Todos los fragmentos de la vista:** muestra también la narración. El selector general marca todas las casillas habilitadas de esa lista.

Se mantiene el filtro por capítulo o escena. Cambiar de modo limpia la selección y detiene la reproducción para evitar operar sobre fragmentos ocultos. Las escenas completas y las exportaciones de capítulo mantienen sus alcances anteriores; esta corrección afecta a la vista y a su selección.

Si no hay candidatos, el primer modo muestra una lista vacía y un mensaje; se puede pulsar «Mostrar todos los fragmentos» para recuperar la narración visible. No se reclasifican narraciones como diálogos automáticamente, no se asignan personajes y no se altera ninguna voz.

## Instalar

Guardar el ZIP en la raíz del proyecto y ejecutar:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Expand-Archive -LiteralPath '.\LIA_AudioMaker_Filtro_v0.1.7.zip' -DestinationPath '.' -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\correccion_filtro\APLICAR.ps1'
```

El script valida todas las sustituciones en memoria antes de escribir, guarda una copia del archivo en `backups\filtro-FECHA` y aplica únicamente las sustituciones concretas. Es idempotente. Si no encuentra los patrones esperados se detiene sin escribir. La ejecución del instalador en un Windows real queda pendiente de verificación allí. Bypass afecta únicamente a ese proceso de PowerShell.

Mantener Vite abierto y recargar con **Ctrl+F5**. No reiniciar Docker ni reimportar el manuscrito. La interfaz mostrará 0.1.7; la API conserva la versión de backend previamente instalada.

## Verificación

- Las seis pruebas del criterio de candidatos pasan.
- TypeScript/Vite compila correctamente.
- Chromium: lista con tres candidatos (dos personajes asignados a frases con clasificación antigua más un pensamiento) y una narración normal. En el modo de candidatos solo aparecen los tres candidatos y «Seleccionar todos» marca los tres, incluidos los del manuscrito y los clips. Se prueba selección parcial y nueva selección completa.
- En el modo completo reaparecen los cuatro fragmentos y se marcan todos. En una escena sin candidatos la lista del primer modo queda vacía; el botón Mostrar todos recupera la narración, que se puede seleccionar en bloque.
- Sin errores JavaScript. No se modificaron manuscritos ni audios.
- El parche exacto reproduce la versión probada al aplicarlo a la fuente 0.1.6; también se comprobó que sus patrones son compatibles con la fuente 0.1.5.
