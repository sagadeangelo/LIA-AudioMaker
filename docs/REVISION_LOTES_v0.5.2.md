# Selección y autorización en lote del análisis · 0.5.2

Base requerida: Plan editorial 0.5.1. Conserva el JSON importado, las decisiones previas, el elenco y los audios.

## Instalación

1. Extrae el ZIP en una carpeta nueva.
2. Ejecuta APLICAR.ps1. Verifica los hashes de todos los archivos antes de aplicar, respalda las fuentes y se detiene ante cambios locales incompatibles.
3. Si termina correctamente, ejecuta ACTUALIZAR_BACKEND.ps1 y espera «Backend listo: 0.5.2».
4. Recarga Ctrl+F5, abre Analizar manuscrito y elige tu análisis en Análisis guardados. No necesitas importar de nuevo el JSON.

## Uso

Abre un rubro del análisis, utiliza la búsqueda si quieres reducir los resultados, y marca las casillas individuales o «Seleccionar todos los pendientes visibles». Después pulsa «Autorizar seleccionados» o «Descartar seleccionados». La confirmación muestra cuántas sugerencias procesará. Cancelar no guarda decisiones.

La selección solo incluye el rubro visible y respeta la búsqueda y el filtro de nombres débiles. Cambiar de rubro, búsqueda, análisis o proyecto limpia la selección. Los elementos ya confirmados o descartados no se incluyen. Los controles individuales siguen disponibles.

## Significado por rubro

- Nombres: autorizar añade nombres nuevos al elenco, con la voz inicial Santa que usa el editor existente. No reasigna diálogos ni cambia perfiles guardados. Los personajes ya existentes, animales y candidatos sin evidencia vinculada no se incorporan en lote como nuevas voces.
- Lugares: guarda la confirmación de las sugerencias.
- Emociones y forma de hablar: guarda su revisión; no cambia automáticamente el tono del TTS.
- Posibles efectos sonoros: guarda confirmación o descarte; no inserta archivos de sonido.
- Plan por escena: las casillas corresponden a los sonidos visibles de las escenas, con el mismo estado compartido del rubro de efectos.
- Escenas actuales: registra su revisión; no modifica las divisiones.
- Lectura editorial: registra la revisión de las unidades localizadas; no autoriza automáticamente sus sonidos ni ejecuta límites nuevos. Las unidades no vinculadas quedan pendientes.
- Posibles cambios de escena: confirmar añade límites entre los fragmentos seleccionados, preservando los límites previos. Los audios se conservan. Al cambiar la estructura el informe queda desactualizado; vuelve a analizar antes de tomar otras decisiones. La acción de deshacer existente permite revertir las divisiones en orden inverso.

## Integridad del lote

El servidor comprueba el proyecto, informe, versión del manuscrito, categoría e identificadores. No guarda el proyecto hasta procesar correctamente todos los elementos. Si encuentra un elemento inválido o una decisión incompatible, no aplica parcialmente el lote. Repetir una confirmación idéntica no duplica sus registros.

## Verificación

78 pruebas backend, 15 frontend y compilación. Prueba en navegador: selección filtrada, cancelar/confirmar, descarte de restantes y revisión de escenas actuales/editoriales con un extracto del manuscrito real. Las pruebas comprueban preservación de WAV, voces y fragmentos, conflictos, informes de otro proyecto, aplicación de múltiples divisiones y restauración. La instalación Windows del usuario se verifica con el actualizador.
