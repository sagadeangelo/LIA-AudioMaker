import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from .scenes import included
from .voice_editor import approved_audio


def export_book(project, data_dir: Path, audio_format: str, partial: bool):
    if audio_format not in ("mp3", "wav"):
        raise HTTPException(422, "Formato inválido")

    if not shutil.which("ffmpeg"):
        raise HTTPException(503, "FFmpeg no está disponible")

    all_segments = [
        s
        for chapter in project.get("chapters", [])
        for s in chapter.get("segments", [])
        if included(s)
    ]

    if not all_segments:
        raise HTTPException(409, "El audiolibro no tiene fragmentos incluidos")

    ready = []
    missing = []

    for s in all_segments:
        name = approved_audio(s)
        if not name:
            missing.append(s)
            continue

        if Path(name).name != name or not name.lower().endswith(".wav"):
            missing.append(s)
            continue

        path = data_dir / name
        if not path.is_file():
            missing.append(s)
            continue

        ready.append(path)

    if missing and not partial:
        raise HTTPException(
            409,
            f"El audiolibro está incompleto: faltan {len(missing)} "
            "fragmentos. Usa la vista previa parcial."
        )

    if not ready:
        raise HTTPException(409, "No hay audios disponibles para exportar")

    temporary = Path(tempfile.mkdtemp(prefix="lia_book_"))
    listing = temporary / "concat.txt"
    output = temporary / ("audiolibro." + audio_format)

    try:
        # Rutas relativas al archivo concat, evitando problemas de comillas.
        links = []

        for index, source in enumerate(ready):
            alias = temporary / f"segment_{index:06d}.wav"
            try:
                os.link(source, alias)
            except OSError:
                shutil.copy2(source, alias)
            links.append(alias.name)

        listing.write_text(
            "".join(f"file '{name}'\n" for name in links),
            encoding="utf-8",
        )

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-nostdin",
            "-f", "concat",
            "-safe", "1",
            "-i", str(listing),
            "-af", "loudnorm=I=-19:TP=-2:LRA=7",
        ]

        if audio_format == "mp3":
            command += ["-codec:a", "libmp3lame", "-b:a", "192k"]
        else:
            command += ["-codec:a", "pcm_s16le"]

        command += ["-y", str(output)]

        subprocess.run(
            command,
            check=True,
            capture_output=True,
            timeout=3600,
        )

        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("FFmpeg no produjo un archivo válido")

        filename = (
            "audiolibro_vista_previa." if partial else "audiolibro_completo."
        ) + audio_format

        return FileResponse(
            output,
            filename=filename,
            media_type="audio/mpeg" if audio_format == "mp3" else "audio/wav",
            background=BackgroundTask(shutil.rmtree, temporary, ignore_errors=True),
        )

    except subprocess.TimeoutExpired:
        shutil.rmtree(temporary, ignore_errors=True)
        raise HTTPException(504, "La exportación excedió el tiempo permitido")
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        detail = (exc.stderr or b"").decode("utf-8", errors="replace")[-600:]
        raise HTTPException(502, "Falló FFmpeg: " + detail)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
