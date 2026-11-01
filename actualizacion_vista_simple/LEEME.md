# LIA AudioMaker 0.1.8 · Vista simple y filtros editoriales

Actualización de interfaz para las instalaciones conocidas 0.1.6 y 0.1.7 basadas en 0.1.6. No modifica backend, base de datos, manuscritos, voces ni audios.

## Cambios

Se retira del editor la opción «Diálogos y candidatos» y su selector de alcance. Al abrir o cambiar de proyecto se muestran **Todos los fragmentos** del capítulo o escena actual.

El selector «Mostrar fragmentos» ofrece filtros explícitos, disponibles tanto en modo individual como múltiple:

- **Todos los fragmentos:** incluye narración y personajes.
- **Sin personaje asignado:** muestra las frases sin hablante o con la etiqueta Sin atribuir/Sin asignar. Narrador cuenta como hablante asignado.
- **Pendientes de revisión:** muestra las frases marcadas para revisión editorial, sea cual sea su hablante.
- **Por personaje:** una opción por cada perfil del elenco, incluido Narrador. Se reconocen las variantes de mayúsculas y acentos del nombre.

El filtro por personaje se conserva al cambiar de capítulo, para poder revisar sus intervenciones en diferentes capítulos. Se restablece Todos al cambiar de proyecto o recargar la aplicación.

## Seleccionar y asignar

1. Abrir el capítulo y, opcionalmente, elegir una escena o filtro editorial.
2. Pulsar «Selección múltiple» para ver las casillas.
3. Marcar una, varias o «Seleccionar todos». La selección general marca todas las casillas habilitadas de la lista visible, sin usar una clasificación de diálogos oculta.
4. Asignar el personaje con una tarjeta del elenco, o quitar los seleccionados si no deben narrarse.

Cambiar el filtro limpia las casillas seleccionadas y detiene la reproducción para evitar actuar sobre contenido oculto. «Mostrar todos» permite salir rápidamente de un filtro sin coincidencias. Al editar el nombre de un personaje dentro de una vista filtrada, el fragmento permanece visible durante la edición y solo cambia de filtro después de guardar.

Mostrar quitados, quitar/restaurar escenas y fragmentos, asignación por arrastre, elenco y papelera de proyectos se conservan. Los registros quitados y separadores no se incluyen en Seleccionar todos, aunque se visualicen para revisión. El filtro solo afecta la vista y la selección: procesar el libro y exportar el capítulo conservan sus alcances previos.

## Instalar en Windows

Guardar el ZIP en la raíz del proyecto y ejecutar:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Expand-Archive -LiteralPath '.\LIA_AudioMaker_VistaSimple_v0.1.8.zip' -DestinationPath '.' -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\actualizacion_vista_simple\APLICAR.ps1'
```

El instalador valida versiones conocidas antes de copiar y respalda los archivos en `backups\vista-simple-FECHA`. Si detecta código distinto se detiene sin sobrescribirlo. Bypass solo afecta al proceso lanzado, no a la política global de PowerShell. Su ejecución en Windows debe comprobarse en el equipo del usuario.

Mantener Vite abierto y recargar con **Ctrl+F5**. No reconstruir Docker ni reimportar el libro. El pie de interfaz indicará 0.1.8; la API conserva su versión anterior.

## Verificado

- 11 pruebas de frontend aprobadas: 5 de los nuevos filtros y 6 de selección conservadas como regresión. Incluyen narración visible por defecto, personajes con clasificación antigua, pendientes de revisión, nombres con acentos, fragmentos quitados y ausencia de mutaciones de datos.
- TypeScript/Vite compila correctamente.
- Chromium: Todos aparece por defecto; se retira el selector anterior; Seleccionar todos marca cuatro fragmentos de una vez; filtrar limpia la selección; filtros sin asignar, revisión y personaje; escritura de nombre estable hasta guardar; coincidencias vacías al cambiar de capítulo y vuelta a Todos; persistencia de la asignación y vista predeterminada al recargar. Sin errores JavaScript.

No se reanalizan ni reclasifican los proyectos y no se regeneran audios al instalar.
