# Plan editorial de Ángelo & El Proyecto Ditóx · Importador 0.5.1

Se preparó a partir del manuscrito pegado por el autor en esta conversación. No requiere Ollama, GPU ni consumo de APIs. El análisis editorial contiene 15 capítulos, 94 unidades de escena propuestas, 128 indicaciones sonoras, 51 fichas humanas y 2 mascotas. Los papeles sin nombre están identificados por rol; no son 51 nombres propios diferentes ni 128 archivos de audio.

## Instalación Windows

Requiere la actualización Lector de escenas 0.5.0. Cierra las ventanas de edición de LIA AudioMaker antes de aplicar los archivos.

1. Copia el ZIP a C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker y extráelo en una carpeta nueva.
2. Ejecuta APLICAR.ps1 de la carpeta extraída. Comprueba todos los hashes antes de escribir, crea respaldo de fuentes y se detiene si hay cambios locales incompatibles. No reemplaza .env, manuscritos, WAV ni volúmenes Docker.
3. Si termina sin error, ejecuta ACTUALIZAR_BACKEND.ps1 del mismo paquete y espera «Backend listo: 0.5.1».
4. Recarga Ctrl+F5 y selecciona el proyecto existente. No vuelvas a importar el manuscrito.

## Importación del JSON en el libro existente

1. Abre Analizar manuscrito → Importar análisis editorial externo.
2. Selecciona Angelo_Ditox_Plan_Editorial_v1.json, incluido en la raíz de este paquete.
3. Revisa cuántos inicios de escena e indicaciones sonoras se pudieron localizar.
4. Expande las coincidencias y las citas pendientes. Una cita puede faltar por edición del texto, estar partida entre dos fragmentos o aparecer varias veces. Nunca se adivina cuál es el fragmento.
5. Si hay pendientes y quieres importar el resto, marca la aceptación de importación parcial. Las citas pendientes permanecen en Lectura editorial, pero sus sonidos no se vinculan automáticamente.
6. Para añadir divisiones, marca «Añadir las divisiones compatibles de escena». Esta opción añade límites entre fragmentos existentes; conserva los límites que ya tenías y no corta fragmentos producidos. Sin marcarla, se guarda solo el plan.
7. Marca la confirmación de revisión y pulsa Guardar plan editorial.
8. Abre Lectura editorial para revisar lugar, capa narrativa, personajes mencionados o presentes, emociones, evidencia y errores sonoros que deben evitarse.
9. En Posibles efectos sonoros o Plan por escena puedes confirmar o descartar los sonidos que sí se vincularon.

El número de escenas actuales puede ser distinto de 94: son 94 unidades editoriales, algunas comienzan dentro de un fragmento, y las divisiones existentes se conservan. Los encabezados originales ESCENA no siempre cubren un único lugar o tiempo.

## Lo que se conserva

La importación no cambia texto, IDs de fragmentos, voces, velocidades, elenco existente, pronunciaciones, revisión de audio, audio activo ni versiones anteriores. No genera ni mezcla sonidos y no vuelve a producir el audiolibro. Añadir una división no necesita regenerar sus audios.

Se conserva el historial de análisis. «Análisis guardados» permite recuperar el plan después de ejecutar otra vez el lector local. Las confirmaciones de informes anteriores no se trasladan automáticamente a sugerencias nuevas.

«Restaurar divisiones anteriores al plan» restaura solo las divisiones de esa importación, siempre que no hayan cambiado después. Conserva cualquier audio posterior. El JSON y la lectura editorial siguen disponibles; el informe puede quedar desactualizado tras restaurar.

## Criterios de lectura

- Abuelo Abelard / Tío Abelard: personas distintas.
- Anastasia madre / Abuela Anastasia: personas distintas.
- Damián hijo de Silvano / Dr. Damián Ditóx: personas distintas.
- André / Andrés: no unir automáticamente.
- Gibran / Gibrán: variante de acentuación, sin reescribir el manuscrito.
- Hilary / Hillary y Dayane / Dayana: variantes probables a confirmar con el autor.
- Edward y Tommy: mascotas, no voces humanas. Edward gruñe, el texto niega que ladre; Tommy aparece muerto.
- DESCONOCIDO en la confrontación inicial del XV es Darién antes de ser reconocida. Los Desconocidos I–IV del recuerdo son otros papeles; IV se oye por radio.
- El doctor de la clínica de Jim no se identifica como Ditóx.
- El nombre del padre de Rachel es Michael Smirnov; no se inventa un nombre para su madre ni para el chofer.
- Francisco Tovar, María Dolores Amaral y Miguel Tovar Amaral son nombres del material del autor, no del reparto de ficción.
- Los personajes de las cinco obras de teatro, las personas en fotos, las amenazas futuras, los sueños y los símiles no están físicamente presentes en el sótano.
- Las edades de Darién tienen discrepancias; no se fija una edad canónica ni se corrige el texto sin revisión editorial.

## Ejemplo de la playa

Oleaje y brisa son ambientes inferidos. Los graznidos están explícitos. Las salpicaduras de aves que se lanzan al agua son una propuesta inferida. Los cruceros lejanos solo se ven; no se añaden bocinas de barco sin evidencia. Más tarde, el celular de Rachel vibra: no se impone una melodía. El silencio de la pareja no obliga a silenciar el mar y las aves.

## Cobertura por capítulo

| Capítulo | Unidades editoriales | Indicaciones sonoras |
|---|---:|---:|
| 1 | 6 | 3 |
| 2 | 5 | 5 |
| 3 | 5 | 4 |
| 4 | 13 | 30 |
| 5 | 3 | 1 |
| 6 | 5 | 7 |
| 7 | 5 | 7 |
| 8 | 5 | 2 |
| 9 | 8 | 10 |
| 10 | 9 | 10 |
| 11 | 8 | 11 |
| 12 | 4 | 10 |
| 13 | 4 | 7 |
| 14 | 7 | 11 |
| 15 | 7 | 10 |

## Límites y verificación

El análisis es una propuesta editorial, no garantía de exhaustividad ni sincronización palabra a palabra. Las indicaciones sonoras incluyen citas, distinción explícito/inferido y notas; todavía necesitan selección de pistas y mezcla supervisada. El texto literario no se corrige.

El plan completo valida contra el esquema del importador. Se comprobaron 74 pruebas backend, 11 frontend, compilación y prueba en navegador con el extracto real de playa. Se verificaron importación, cuatro indicaciones sonoras, división, restauración y conservación de datos. También hay pruebas de WAV conservado, citas ambiguas, versiones cambiadas e importación a un proyecto diferente.

No se ha leído la base de datos del Windows del autor; las coincidencias completas del libro se comprueban en la vista previa de su instalación. Una coincidencia normaliza mayúsculas, acentos y puntuación, pero exige cita contigua dentro de un fragmento del capítulo correcto. Si coincide menos de la mitad de los inicios, bloquea la importación.

## Siguiente etapa

Después de revisar las coincidencias, usar los sonidos confirmados para incorporar un catálogo de pistas con licencia adecuada, volumen, fundidos, duración y preescucha de la mezcla. No se instalan modelos locales en esta entrega.
