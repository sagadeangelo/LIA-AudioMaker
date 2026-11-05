# Música por capítulo · 0.6.23

Requiere v0.6.22. En LIA Sound Effects → Música de fondo, antes del selector de escena aparece Volumen de música por capítulo. Elige capítulo, ajusta el deslizador o el número de -40 a 0 dB y pulsa Aplicar a todas las escenas del capítulo. Se propone -18 cuando no hay una preferencia guardada; no se cambia ningún volumen hasta aplicar.

Guarda el valor por capítulo y actualiza únicamente sus pistas con role music, incluidas las desactivadas, y las elecciones pendientes de sus escenas incluidas. Reinicia a cero el balance adicional music_db de esas escenas para que -18 no se sume a otra atenuación. Conserva narración, efectos, archivos, fragmentos y demás capítulos. Las nuevas elecciones sin volumen explícito y los uploads asociados a esas escenas heredan el valor; un valor explícito o ajuste individual sigue teniendo prioridad. Aplicar de nuevo a todo el capítulo reemplaza las excepciones de escena.

Para oír el resultado, elige una escena del capítulo y genera su preescucha. Se usan los volúmenes guardados, no el deslizador sin aplicar. El reproductor aparece al terminar; requiere narración aprobada y alguna pista activa, bajo los límites habituales del mezclador. No genera de golpe una preescucha concatenada del capítulo entero.

Las mezclas antiguas se conservan y las vistas del mezclador las marcan obsoletas al cambiar sus pistas o balance. Las descargas ya hechas permanecen iguales y necesitan una nueva exportación. Las exportaciones de la prueba automática siguen conservadas; no escuchar una exportación anterior esperando un cambio retroactivo.

Espera a finalizar una producción automática antes de editar volúmenes. El endpoint rechaza mezclas activas y producciones sin terminar para conservar su reanudación. Cambiar asignaciones después de exportar el contexto de IA vuelve obsoleta la huella de recursos del plan: exporta un contexto actualizado y ajusta el plan antes de ejecutar. No modificar tokens para evitar esta comprobación.

Instalación: ACTUALIZAR.ps1 respalda fuentes, ejecuta pruebas aisladas y de interfaz, compila y reinicia backend. No aplica volúmenes a datos del usuario ni toca audios, credenciales o iniciador durante la instalación. Ctrl+F5 después. Pruebas automatizadas locales; inspección visual Windows pendiente.
