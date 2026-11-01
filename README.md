# LIA AudioMaker · 0.1.0

Primera implementación ejecutable del estudio de audiolibros. Raíz Windows prevista: `C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker`.

Incluye API FastAPI, React/TypeScript/Vite, almacenamiento persistente SQLAlchemy, extracción TXT/DOCX/PDF/EPUB, revisión de atribuciones, generación local eSpeak NG, versiones de audio y exportación FFmpeg. La interfaz muestra formas de onda calculadas sobre el WAV real. Los diálogos ambiguos exigen revisión; no se inventa su hablante.

**Es una versión inicial, no el MVP completo del prompt maestro.** El análisis es heurístico y la síntesis es básica, sin actuación emocional. Ver `docs/ESTADO.md` para límites concretos.

## Inicio Windows

Extraer este proyecto en la ruta indicada, sin sobrescribir un repositorio existente. Leer `docs/INSTALACION_WINDOWS.md`.

Opción con Docker (PostgreSQL + eSpeak NG + FFmpeg en backend):

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
Copy-Item .env.example .env
notepad .env
docker compose up --build -d
.\scripts\INICIAR_FRONTEND.ps1
```

Abrir http://127.0.0.1:5173. API: http://127.0.0.1:8000/docs.

Opción sin Docker: ejecutar `scripts/INICIAR_BACKEND.ps1` y `scripts/INICIAR_FRONTEND.ps1` en terminales distintas. Usa SQLite persistente por defecto; para producir voz requiere eSpeak NG y FFmpeg en PATH.

## Comprobar

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Set-Location ..\frontend
npm run build
```

`backend/data` o el volumen Docker contienen originales extraídos, metadatos y audio. No borrarlos. Respaldar conjuntamente base de datos y archivos de audio. Aplicación para uso local; no exponer a Internet sin autenticación y límites de recursos.
