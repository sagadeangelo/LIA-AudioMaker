# LIA AudioMaker · Corrección de selección 0.1.5

Corrección de interfaz para la versión 0.1.4. No cambia la API ni los datos; el backend mantiene la versión 0.1.4.

## Problema corregido

El modo «Diálogos y candidatos» se basaba principalmente en `kind`. Un fragmento detectado inicialmente como narración podía recibir un personaje manualmente, conservar `kind=narration` y quedar fuera del selector. Si todos los fragmentos de la vista estaban así, «Seleccionar todos» quedaba desactivado aunque mostraran nombres de personajes.

Ahora el selector considera también el personaje asignado y los indicadores explícitos del texto fuente en proyectos antiguos. Incluye pensamientos y acotaciones candidatas. Sigue excluyendo narración normal del Narrador y registros quitados o separadores estructurales.

La casilla muestra el número de fragmentos elegibles y estado parcial cuando solo algunos están seleccionados. Si la vista contiene únicamente narración, el modo de diálogos sigue sin tener elementos seleccionables, pero ahora lo explica. En ese caso elegir «Todos los fragmentos de la vista» o marcar las frases individualmente.

Los dos modos siguen teniendo el alcance del capítulo o escena visible. No se reanaliza el libro, no se reasignan voces y no se regeneran audios.

## Instalar

Guardar el ZIP en `C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker` y ejecutar:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Expand-Archive -LiteralPath '.\LIA_AudioMaker_Seleccion_v0.1.5.zip' -DestinationPath '.' -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\correccion_seleccion\APLICAR.ps1'
```

El script valida versiones conocidas, respalda los archivos anteriores y copia solo archivos de interfaz. No reconstruye Docker. Bypass aplica solo al proceso lanzado, no a la política global. La ejecución del instalador en Windows queda por verificar allí.

Mantener Vite abierto y recargar con **Ctrl+F5**. Si se había detenido, ejecutar `npm.cmd run dev` desde `frontend`. No se necesita reimportar el libro. El pie de la interfaz mostrará 0.1.5.

## Verificado

- Seis pruebas del selector aprobadas con Node.js: personaje sobre clasificación antigua, narración normal, pensamientos/acotaciones, proyectos antiguos con etiquetas y comillas, exclusión de registros quitados/separadores y ambos alcances.
- TypeScript/Vite compila correctamente.
- Chromium: reproducción del caso con Ana asignada a un fragmento que aún conserva `kind=narration`; selección correcta en modo diálogo, exclusión de narración normal, selección de todos en modo completo, estado parcial y mensaje cuando la escena no tiene candidatos. Sin errores JavaScript.

Prueba opcional, con Node 24 o posterior, desde frontend:

```powershell
node --experimental-strip-types --test tests/selection.test.mjs
```
