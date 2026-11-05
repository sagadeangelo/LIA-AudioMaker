import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import wave
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from .scenes import included
from .voice_editor import approved_audio

LOCK = threading.RLock()
JOBS = {}
MAX_ACTIVE = 1
TTL = 3600


def cleanup():
    now = time.time()
    with LOCK:
        expired = [
            key for key, job in JOBS.items()
            if job["status"] in ("ready", "error", "downloaded")
            and now - job["updated"] > TTL
        ]
        for key in expired:
            job = JOBS.pop(key)
            if job.get("folder"):
                shutil.rmtree(job["folder"], ignore_errors=True)


def update(job_id, **changes):
    with LOCK:
        job = JOBS[job_id]
        job.update(changes)
        job["updated"] = time.time()


def public(job):
    return {
        "id": job["id"],
        "status": job["status"],
        "percent": job["percent"],
        "message": job["message"],
        "format": job["format"],
        "segments": job["segments"],
    }


def start(project, data_dir, audio_format, partial):
    cleanup()

    if audio_format not in ("mp3", "wav"):
        raise HTTPException(422, "Formato invalido")

    if not shutil.which("ffmpeg"):
        raise HTTPException(503, "FFmpeg no disponible")

    ready = []
    missing = 0

    for chapter in project.get("chapters", []):
        for segment in chapter.get("segments", []):
            if not included(segment):
                continue

            name = approved_audio(segment)

            if not isinstance(name, str) or Path(name).name != name:
                missing += 1
                continue

            if not name.lower().endswith(".wav"):
                missing += 1
                continue

            path = Path(data_dir) / name

            if path.is_file():
                ready.append(path)
            else:
                missing += 1

    if not ready:
        raise HTTPException(409, "No hay audios disponibles")

    if missing and not partial:
        raise HTTPException(
            409, f"Faltan {missing} fragmentos. Usa vista previa parcial."
        )

    with LOCK:
        if sum(
            job["status"] in ("preparing", "processing")
            for job in JOBS.values()
        ) >= MAX_ACTIVE:
            raise HTTPException(
                409, "Ya existe una exportacion en proceso."
            )

        job_id = str(uuid.uuid4())

        JOBS[job_id] = {
            "id": job_id,
            "status": "preparing",
            "percent": 0,
            "message": "Preparando fragmentos",
            "format": audio_format,
            "segments": len(ready),
            "folder": None,
            "updated": time.time(),
        }

    thread = threading.Thread(
        target=worker,
        args=(job_id, ready, audio_format, partial),
        daemon=True,
    )
    thread.start()

    return public(JOBS[job_id])


def worker(job_id, ready, audio_format, partial):
    folder = None

    try:
        folder = Path(tempfile.mkdtemp(prefix="lia_export_job_"))
        update(job_id, folder=folder)

        total_seconds = 0.0
        names = []

        for index, source in enumerate(ready):
            alias = folder / f"segment_{index:06d}.wav"

            try:
                os.link(source, alias)
            except OSError:
                shutil.copy2(source, alias)

            with wave.open(str(source), "rb") as audio:
                total_seconds += (
                    audio.getnframes() / audio.getframerate()
                )

            names.append(alias.name)

            if index % 25 == 0:
                update(
                    job_id,
                    percent=min(5, int(5 * index / len(ready))),
                )

        listing = folder / "concat.txt"
        listing.write_text(
            "".join("file '" + name + "'\n" for name in names),
            encoding="utf-8",
        )

        output = folder / ("audiolibro." + audio_format)

        command = [
            "ffmpeg", "-hide_banner",
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

        command += [
            "-progress", "pipe:1",
            "-nostats",
            "-y", str(output),
        ]

        update(
            job_id,
            status="processing",
            percent=5,
            message="Procesando audio con FFmpeg",
        )

        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        ) as process:
            started = time.monotonic()

            for line in process.stdout:
                if time.monotonic() - started > 3600:
                    process.kill()
                    raise RuntimeError("Tiempo de exportacion excedido")

                line = line.strip()

                if line.startswith("out_time_us="):
                    try:
                        seconds = int(line.split("=", 1)[1]) / 1000000
                        percent = 5 + int(
                            94 * min(1, seconds / max(total_seconds, 1))
                        )
                        update(job_id, percent=min(99, percent))
                    except ValueError:
                        pass

            return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(
                f"FFmpeg termino con codigo {return_code}"
            )

        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("No se genero un archivo valido")

        update(
            job_id,
            status="ready",
            percent=100,
            message="Archivo listo para descargar",
        )

    except Exception as exc:
        update(
            job_id,
            status="error",
            message=str(exc),
        )

        if folder:
            shutil.rmtree(folder, ignore_errors=True)
            update(job_id, folder=None)


def status(job_id):
    cleanup()

    with LOCK:
        job = JOBS.get(job_id)

        if not job:
            raise HTTPException(404, "Trabajo no encontrado")

        return public(job)


def download(job_id):
    cleanup()

    with LOCK:
        job = JOBS.get(job_id)

        if not job:
            raise HTTPException(404, "Trabajo no encontrado")

        if job["status"] != "ready":
            raise HTTPException(409, "Archivo aun no disponible")

        folder = job["folder"]
        audio_format = job["format"]

    output = folder / ("audiolibro." + audio_format)

    if not output.is_file():
        raise HTTPException(404, "Archivo temporal no encontrado")

    def finish():
        with LOCK:
            current = JOBS.get(job_id)
            if current:
                current["status"] = "downloaded"
                current["updated"] = time.time()

    return FileResponse(
        output,
        filename="LIA_AudioMaker_Audiolibro." + audio_format,
        media_type=(
            "audio/mpeg" if audio_format == "mp3" else "audio/wav"
        ),
        background=BackgroundTask(finish),
    )
