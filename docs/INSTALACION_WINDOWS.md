# Instalación Windows 11

## Preparar la carpeta

Este trabajo se creó en un entorno Linux temporal; no se modificó el disco C: del propietario. Antes de extraer el ZIP, revisar si existe `C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker`. Si contiene archivos, respaldarlos y comparar antes de copiar. No crear otro proyecto paralelo en Windows.

El ZIP contiene una carpeta raíz `lia_audiomaker`: su contenido debe quedar directamente en la ruta indicada, sin duplicar el nombre de carpeta.

## Ruta recomendada con Docker

Necesita Docker Desktop en ejecución y Node.js con npm. En PowerShell:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Copy-Item .env.example .env
notepad .env
```

Cambiar POSTGRES_PASSWORD por una contraseña propia con letras y números. No subir `.env` a GitHub. Después:

```powershell
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/api/health
.\scripts\INICIAR_FRONTEND.ps1
```

Abrir http://127.0.0.1:5173. Docker instala eSpeak NG y FFmpeg dentro del backend. Esta ruta está preparada pero no ejecutada en el entorno de construcción, que no dispone de Docker.

## Ruta Python local

Necesita Python 3.12, Node.js, eSpeak NG y FFmpeg instalados. Obtener eSpeak NG de https://github.com/espeak-ng/espeak-ng/releases y FFmpeg de https://ffmpeg.org/download.html. Agregar sus carpetas ejecutables a PATH y abrir nuevas terminales.

```powershell
Get-Command py, node, npm, espeak-ng, ffmpeg
.\scripts\INICIAR_BACKEND.ps1
```

En otra terminal, desde la raíz:

```powershell
.\scripts\INICIAR_FRONTEND.ps1
```

Si PowerShell bloquea los scripts, se pueden ejecutar manualmente los comandos del script en la terminal. No es necesario cambiar la política global. El backend local guarda sus datos en `backend\data` y usa SQLite; no lanzar a la vez backend Docker y local en el mismo puerto.

## Primer audiolibro

1. Pulsar «＋ Proyecto» y escribir un título.
2. Importar `samples/manuscrito.txt`.
3. Seleccionar el capítulo y cada diálogo marcado «Revisar».
4. Escribir Ana o Marcos según la evidencia del texto; asignar voces distintas, por ejemplo `es+f2` y `es+m3`.
5. Guardar la asignación. Elegir cada fragmento y generar su audio.
6. La forma de onda aparece solo cuando existe un WAV real. Pulsar el clip para escucharlo.
7. Regenerar un fragmento conserva las versiones anteriores en disco. La interfaz aún no permite restaurarlas.
8. Una vez generados todos los fragmentos, exportar WAV o MP3.
9. Reiniciar backend y frontend y abrir el proyecto para comprobar persistencia.

## Errores habituales

- «Motor TTS no disponible»: verificar `espeak-ng --version` en la misma terminal del backend. En Docker reconstruir la imagen.
- PDF sin texto: requiere OCR externo; esta versión no lo incorpora.
- No se puede exportar: generar todos los segmentos y comprobar FFmpeg.
- No hay conexión: revisar backend en puerto 8000 y proxy Vite. El frontend no lleva datos de demostración simulados.
- Puerto ocupado: detener la otra instancia; no eliminar datos para solucionarlo.
- Base PostgreSQL: la contraseña interpolada en la URL debe ser URL-safe. La configuración propuesta utiliza letras y números.

No se probó la ejecución de estos scripts en un Windows real durante esta entrega.
