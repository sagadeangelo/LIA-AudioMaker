# Aislar pruebas y revisar proyectos de prueba

Corrección independiente para la instalación actual de LIA AudioMaker. No actualiza las funciones de sonidos a 0.6.3, no cambia la versión de la aplicación y no reemplaza su iniciador.

## Qué corrige

`backend/tests/conftest.py` ahora crea una carpeta temporal nueva y fuerza **DATABASE_URL y DATA_DIR** antes de importar la aplicación. La suite de pruebas usa SQLite privado y archivos temporales, aunque Compose le haya pasado la conexión de PostgreSQL. Si la aplicación se importó antes de instalar este aislamiento, la ejecución se detiene. No modifica .env ni la conexión del backend que sirve tu libro.

La base temporal sirve para las pruebas unitarias de esta suite. No equivale a validar una integración PostgreSQL. No se habilitan pruebas contra la base de tus proyectos.

## Aplicar y revisar

1. Extrae el ZIP y ejecuta `APLICAR.ps1 -Repo 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'`.
2. Ejecuta desde tu proyecto:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Revisar-Proyectos-Prueba.ps1
```

Se ejecuta un contenedor temporal con la imagen backend existente, sin iniciar otros servicios ni importar el arranque de FastAPI. La revisión usa SELECT; en PostgreSQL la transacción se declara de solo lectura. Guarda un informe JSON y CSV en `mantenimiento\proyectos_FECHA` y muestra líneas **CANDIDATO** con los IDs.

**Esta revisión no mueve ni borra proyectos.** Puedes compartir las líneas CANDIDATO; no hace falta compartir la base de datos, .env ni los manuscritos.

## Cómo identifica candidatos

Comprueba tanto el nombre exacto como el texto completo de las dos muestras verificadas en el código:

- Revisión en lote: el texto corto que empieza `CAPÍTULO I / LA PRUEBA / Lindsay dijo que Gibrán estaba en la playa…`.
- Editor fixture: los dos capítulos cortos con `ANA: Ditóx vuelve`, `ANA: Ditóx sale` y `MARCOS: Ditóx espera`.

Otros nombres o textos no coincidentes quedan para conservar. Un proyecto con el mismo nombre pero otro manuscrito no se considera candidato. Si tiene recursos de sonido o mezclas, también queda protegido para revisión individual. Los proyectos ya enviados a papelera no se vuelven a modificar.

No se usa una búsqueda genérica de “Ángelo”, “Ditóx”, “prueba” o “fixture” para eliminar proyectos. Que un proyecto no sea candidato no demuestra que sea real: solo indica que esta herramienta no puede identificarlo de forma segura.

## Enviar a papelera los IDs revisados

Una vez revisado el informe, usa **sus IDs concretos**, nunca los ejemplos literales:

```powershell
.\scripts\Revisar-Proyectos-Prueba.ps1 -Modo Papelera `
    -Informe 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker\mantenimiento\proyectos_FECHA\informe_proyectos.json' `
    -Ids 'ID_REVISADO_1','ID_REVISADO_2'
```

La herramienta vuelve a comprobar cada ID, el contenido y la huella de la versión registrada. Si algún proyecto cambió desde el informe, se rechaza el lote. Antes de la primera escritura guarda `respaldo_papelera.json` con los documentos originales completos. Después marca `deleted_at` en una transacción: los proyectos salen de la lista activa y quedan en la Papelera de LIA.

No elimina registros, trabajos, manuscritos ni archivos de audio. El respaldo contiene los documentos originales; consérvalo localmente y no lo subas al repositorio público.

## Restaurar

Puedes usar el botón de restauración en Papelera de LIA. Alternativamente:

```powershell
.\scripts\Revisar-Proyectos-Prueba.ps1 -Modo Restaurar `
    -Respaldo 'C:\RUTA\DEL\RESULTADO\respaldo_papelera.json'
```

El respaldo solo se restaura si el proyecto sigue exactamente en el estado que dejó la herramienta, o ya está restaurado. Si hubo cambios posteriores, se detiene para no sobrescribirlos. No uses eliminación definitiva de la Papelera para esta limpieza.

## Ejecutar pruebas a partir de ahora

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Probar-Aislado.ps1
```

Monta el código, las pruebas y las herramientas actuales como solo lectura en un contenedor temporal. Define una base SQLite de respaldo, y conftest vuelve a crear su base privada por ejecución. No se necesita reconstruir el backend para este arreglo: las pruebas se montan desde Windows. El backend de uso habitual sigue empleando PostgreSQL.

## Verificación de desarrollo

Siete pruebas nuevas verificaron: sustitución de conexión heredada antes de importar FastAPI, preservación de una base SQLite que simulaba producción, ausencia de conexión a PostgreSQL heredado, revisión sin escrituras, identificación estricta, protección de proyectos reales con nombres similares, envío reversible a papelera, restauración y rechazo de lotes o respaldos que sobrescribirían cambios posteriores.

No se accedió desde aquí a tu PostgreSQL Windows. El inventario real se obtendrá al ejecutar Revisar-Proyectos-Prueba.ps1 en tu computadora. No se han enviado proyectos reales a papelera durante la preparación del paquete.
