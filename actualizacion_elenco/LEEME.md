# LIA AudioMaker 0.1.2 · Elenco y asignación por arrastre

Actualización para la versión 0.1.1 instalada. No requiere reimportar el libro ni reiniciar la base de datos.

## Instalar

Guardar `LIA_AudioMaker_Elenco_v0.1.2.zip` en `C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker` y ejecutar:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Expand-Archive -LiteralPath '.\LIA_AudioMaker_Elenco_v0.1.2.zip' -DestinationPath '.' -Force
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\actualizacion_elenco\APLICAR.ps1'
```

El instalador verifica que los archivos correspondan a versiones conocidas. Si hay modificaciones distintas, se detiene antes de copiar. Respalda el código anterior en `backups\elenco-FECHA` y reconstruye el backend. No modifica `.env`, los volúmenes, manuscritos ni audios. La política Bypass afecta únicamente al proceso lanzado; no cambia la política global de Windows. El instalador está preparado para PowerShell, pero su ejecución en el Windows del propietario debe verificarse allí.

Mantener el frontend Vite abierto y recargar el navegador. Si se había detenido:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker\frontend'
npm.cmd run dev
```

## Usar

1. Abrir un proyecto existente. El panel derecho muestra «Elenco del libro», con perfiles de todos los capítulos y Narrador. Busca por nombre si la lista es larga.
2. Arrastrar una tarjeta sobre el párrafo del manuscrito (panel izquierdo) o la fila del clip (área central). El destino se resalta.
3. Al soltar se guarda el nombre, voz, velocidad y color del personaje **solo en ese fragmento**. El mensaje de guardado aparece tras la respuesta del backend. No es necesario pulsar Guardar asignación de nuevo.
4. Alternativa accesible: seleccionar un fragmento y pulsar el nombre del personaje. Funciona con teclado mediante Tab y Enter, y con clic o toque.
5. «Deshacer asignación» restaura el estado anterior de la última asignación realizada en esta sesión. Si el fragmento fue editado o regenerado después, el backend rechaza deshacer para no sobrescribir cambios posteriores. Tras recargar no se muestra el botón de deshacer anterior.
6. «Configurar» permite guardar voz, velocidad y color por personaje. Se aplican al asignar su tarjeta; no cambian en masa fragmentos ya asignados ni regeneran audio.
7. «+ Personaje» permite agregar un nombre que no estaba detectado. Guardarlo y cerrar su configuración para continuar.
8. Para un pensamiento, cita o acotación pendiente, asignar el hablante no confirma la revisión del contenido. Revisar el texto, marcar «Confirmo la revisión del contenido y las acotaciones» y pulsar «Guardar asignación». No confirmar automáticamente si se necesita dividir el fragmento: todavía no hay editor manual de cortes.

## Audio y conservación

- Cambiar hablante, voz o velocidad deja el audio anterior como versión histórica y marca el fragmento para regenerar. No borra los archivos WAV.
- Deshacer antes de otra edición/regeneración recupera la referencia al audio anterior y su duración.
- Un cambio solo de color no descarta el audio.
- Asignar detiene la reproducción actual para evitar confundirla con la nueva voz asignada.
- Los demás fragmentos, capítulos y asignaciones no cambian.

## Verificado

- 15 pruebas automatizadas aprobadas, incluyendo flujo TTS/exportación anterior, compatibilidad con proyectos sin catálogo, perfiles persistentes en proceso nuevo, asignación individual, restauración de audio al deshacer, conflictos de edición, datos inválidos y revisión editorial separada.
- TypeScript/Vite compila correctamente.
- Navegador Chromium: arrastre HTML5 real sobre un clip sin seleccionarlo antes; deshacer; asignación por Enter; personajes de otros capítulos; configuración de perfil; nuevo personaje; buscador; datos al recargar; revisión editorial explícita. Sin errores JavaScript.
- Importación del libro completo del propietario: 24 perfiles (incluido Narrador) a partir de nombres atribuidos en sus 15 capítulos. La prueba no altera el archivo del autor.

## Límites

El elenco reúne nombres que el importador ya atribuyó y nombres agregados manualmente. No descubre automáticamente todas las personas mencionadas en prosa ni decide que dos roles sean la misma persona. Los posibles duplicados como «El Doctor» y «Dr. Ditox» conservan perfiles distintos. Unir o renombrar perfiles globalmente no está implementado; la configuración mantiene el nombre existente.

El botón de asignación es la alternativa para pantallas táctiles, donde el arrastre HTML5 puede variar. El guardado requiere conexión al backend: un fallo se muestra como error y no se anuncia como guardado. La aplicación continúa siendo para uso local con un solo proceso backend.
