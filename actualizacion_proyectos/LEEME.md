# LIA AudioMaker 0.1.6 · Eliminar y restaurar proyectos

Actualización para instalaciones conocidas 0.1.4 o 0.1.5. Incluye la corrección del selector de 0.1.5.

## Instalar

Guardar `LIA_AudioMaker_Proyectos_v0.1.6.zip` en la raíz del proyecto y ejecutar:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Expand-Archive -LiteralPath '.\LIA_AudioMaker_Proyectos_v0.1.6.zip' -DestinationPath '.' -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\actualizacion_proyectos\APLICAR.ps1'
```

El instalador verifica las versiones conocidas, respalda el código en `backups\proyectos-FECHA` y reconstruye el backend. No toca `.env` ni elimina volúmenes o datos. Bypass solo afecta al proceso lanzado, no a la política global. La ejecución del instalador en el Windows del propietario debe verificarse allí.

Mantener Vite abierto y recargar el navegador con Ctrl+F5. No hace falta reimportar los libros.

## Eliminar un proyecto

1. Elegir el proyecto en el selector superior.
2. Pulsar **Eliminar proyecto**.
3. La aplicación muestra su nombre y pide confirmar el envío a la papelera.
4. Si se confirma, desaparece de la biblioteca y se cierra su editor. Si se cancela, no se cambia nada.

Solo se elimina de la biblioteca el proyecto seleccionado. El botón está desactivado cuando no hay proyecto abierto o se está procesando una acción.

## Restaurar

1. Pulsar **Papelera** en la barra superior.
2. Localizar el proyecto por su nombre y fecha de eliminación.
3. Pulsar **Restaurar**. Vuelve a la biblioteca y se abre para continuar trabajando.

La eliminación es lógica y reversible. Conserva el archivo importado, texto original, capítulos, personajes, voces, atribuciones, fragmentos quitados, versiones y archivos de audio. No libera espacio en disco ni ofrece borrado permanente en esta versión.

Un proyecto en la papelera no se puede abrir, editar, generar o exportar por sus rutas de proyecto hasta restaurarlo. Los WAV históricos se conservan y las descargas externas anteriores no se invalidan. La papelera se guarda en la misma base de datos y permanece tras reiniciar.

## Aviso del selector

«Seleccionar todos (0)» indica que el modo activo no encontró candidatos elegibles en la vista actual, que puede estar limitada a una escena. El modo «Todos los fragmentos de la vista» sí incluye narración normal. Si existen frases con un personaje asignado que antes se clasificaron como narración, la corrección 0.1.5 incluida en este paquete las tiene en cuenta.

## Verificado

- 26 pruebas de backend aprobadas. Incluyen retirada de la biblioteca, papelera persistente entre procesos, bloqueo de edición del proyecto eliminado, restauración con manuscrito y audio intactos, eliminación repetida idempotente y conservación de otros proyectos.
- Las 6 pruebas del selector siguen aprobadas.
- TypeScript/Vite compila correctamente.
- Chromium: cancelar confirmación no elimina; confirmar retira solo el proyecto elegido; biblioteca y papelera correctas al recargar; restauración recupera editor y manuscrito; estado de papelera vacía. Sin errores JavaScript.

La estructura de almacenamiento existente se mantiene; no se necesita crear tablas nuevas para la marca de papelera.
