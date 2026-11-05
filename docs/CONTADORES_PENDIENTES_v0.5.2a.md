# Contadores de pendientes · parche de interfaz 0.5.2a

Base: 0.5.2. El backend continúa en 0.5.2; no requiere reconstruir Docker.

## Instalación

Extrae el ZIP en una carpeta nueva y ejecuta APLICAR.ps1. El aplicador verifica los archivos, respalda las fuentes y se detiene ante cambios incompatibles. Después recarga con Ctrl+F5. Abre Analizar manuscrito y selecciona el análisis guardado; no vuelvas a importar el JSON ni autorices otra vez los registros ya revisados.

## Cambios

- Las pestañas indican los pendientes autorizables, en lugar del total del informe.
- Autorizar o descartar individualmente o en lote reduce el contador inmediatamente.
- Si todos se revisaron, el rubro queda en cero y muestra «Sin pendientes para autorizar en este rubro».
- Los registros revisados se ocultan por defecto. «Mostrar revisados y referencias» permite consultarlos sin eliminarlos.
- Reconoce las decisiones ya guardadas en el proyecto, incluso al recargar.
- La búsqueda reduce la lista y la selección visible; no cambia el contador global de pendientes del rubro.
- Plan por escena cuenta sonidos pendientes y comparte decisiones con Posibles efectos sonoros.
- Personajes ya existentes, animales y unidades editoriales sin coincidencia no se cuentan como pendientes autorizables. Se muestran como referencias separadas, sin falsificar una autorización. Las citas sin vincular permanecen señaladas.
- El resumen superior del manuscrito sigue indicando totales estructurales. El resumen del rubro distingue pendientes, revisados, referencias y total.

Se conservan datos, audios, voces, pronunciaciones, análisis y decisiones. No se modifica el backend ni se regenera audio.

## Verificación

18 pruebas frontend y compilación. Prueba en navegador: 93 lugares autorizados pasan de 93 a 0, permanecen en cero tras recargar y pueden verse con el control de historial. También se comprobaron búsqueda, autorización individual y descarte por lote con sincronización entre el plan y el listado de sonidos. No se alteraron los fragmentos del manuscrito de laboratorio.
