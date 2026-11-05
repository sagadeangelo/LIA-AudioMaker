# Biblioteca de medios y prioridad de voz · 0.6.27

Actualización conjunta desde v0.6.25; incluye la protección de voz que se estaba preparando en 0.6.26. No necesitas instalar 0.6.26 por separado.

## Biblioteca de medios

Nuevo botón en la cabecera: Biblioteca de medios. Sus rubros son Música, Efectos de sonido y Voces. El catálogo se guarda de forma persistente en una nueva tabla de la base de datos; no se crean proyectos de prueba ni se importan automáticamente todos los archivos al instalar.

Para organizar recursos existentes: selecciona el proyecto, abre la biblioteca, elige el rubro y selecciona un recurso del proyecto actual. Escribe nombre y género/categoría y pulsa Guardar en biblioteca de medios. Los géneros de música y las categorías de efectos admiten texto libre. Puedes buscar, escuchar y editar cada recurso.

Guardar un archivo en el catálogo conserva una copia independiente del WAV junto con créditos, autor, licencia y procedencia; consume espacio adicional. Deduplica archivos idénticos con los mismos autor y licencia. Al usarlo en otro proyecto, crea una copia propia para ese proyecto y evita repetir la importación del mismo recurso. Esto permite conservar el catálogo aunque se elimine el proyecto original y evita que eliminar un proyecto borre el archivo central. No hay borrado definitivo de medios en esta entrega.

Subir mi música / Subir mi efecto usa la carga existente del proyecto seleccionado. Después de subir, clasifica y guarda el recurso en el catálogo central. Buscar y descargar en Freesound abre el buscador existente del proyecto: descarga allí y vuelve a la biblioteca para clasificar. Se conservan sus requisitos de conexión, límites de archivo y datos de licencia.

Usar en el proyecto actual deja el archivo disponible en su biblioteca; no lo aplica a una escena ni reemplaza música automáticamente. Después elige la escena y aplica el recurso con los controles de sonido. Editar una clasificación central actualiza los metadatos de los recursos vinculados de los proyectos; no cambia sus ganancias ni archivos.

Voces: selecciona una voz compatible, ponle un nombre y clasifica género (Mujer, Hombre o Sin clasificar), edad (Niño, Adulto, Adulto mayor o Sin clasificar) y uso (Narrador, Personaje o Ambos). Género y edad son campos independientes. Consultar catálogo de voces obtiene los IDs disponibles de los motores; no genera audio. Esta clasificación es declarada por el usuario: no verifica timbre, no clona voces ni instala modelos. Los perfiles guardados y las categorías de archivos del proyecto se incluyen en el contexto exportado para IA. Todavía no se agrega un nuevo asignador automático universal.

Cambiar clasificaciones vinculadas o importar recursos puede invalidar el token de recursos de un plan anterior. Organiza la biblioteca antes de exportar el contexto actualizado. No alteres tokens manualmente. Durante mezclas activas se bloquean las operaciones que alteran los recursos de los proyectos.

## Prioridad de voz

Activada por defecto en mezclas nuevas. Música de fondo y Montaje y exportación incluyen Priorizar voces automáticamente. Se puede configurar por capítulo o por escena: Suave, Equilibrada o Fuerte. Una escena con ajuste propio prevalece sobre su capítulo. Usar ajuste del capítulo elimina la excepción. Los volúmenes que eligió el usuario y los archivos originales se conservan.

Mide el nivel medio de narración y fondos, reduce únicamente los fondos que superan un techo relativo y aplica compresión sidechain durante el habla. En pausas recupera suavemente su nivel base protegido. La música tiene un techo más conservador que los efectos puntuales. Si la narración es prácticamente silenciosa se evita calcular una reducción falsa. El procesamiento añade análisis y puede hacer que la mezcla tarde más. No garantiza inteligibilidad perfecta ni reemplaza la escucha final.

Las preescuchas y mezclas previas se marcan desactualizadas por la nueva configuración. No se reescriben MP3/WAV antiguos. Genera una preescucha nueva; para la lluvia fuerte del piloto prueba Fuerte y luego vuelve a exportar el proyecto. No se regeneran voces por aplicar esta protección.

## Instalación y comprobación

ACTUALIZAR.ps1 -Repo con la ruta habitual. Respalda fuentes conocidas, ejecuta pruebas aisladas y de interfaz, compila y reconstruye/reinicia backend. Instala sin producciones activas. No se modifican proyectos, audios, credenciales ni iniciador al aplicar las fuentes. La inicialización crea la tabla de catálogo vacía y conserva los volúmenes de Docker.

Pruebas locales: catálogo persistente y deduplicación, copias independientes entre proyectos, conservación de archivos centrales al retirar archivos de origen, metadatos exportables, perfiles de voz, propagación de categorías y validación de referencias. Para la protección, FFmpeg real verifica reducción del fondo durante voz, recuperación en pausas, conservación de la componente de voz respecto al remuestreo normal y hashes originales. Interfaz compilada; revisión visual y escucha con los archivos reales del usuario pendientes.
