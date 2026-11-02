"""Proveedor Kokoro TTS para LIA AudioMaker."""

import json
import os
import urllib.error
import urllib.request
import wave
from pathlib import Path


KOKORO_URL = os.getenv(
    "KOKORO_URL",
    "http://lia_audiomaker_kokoro:8880"
).rstrip("/")

SPANISH_VOICES = {
    "em_santa",
    "em_alex",
    "ef_dora",
}


class KokoroError(Exception):
    """Error de generacion o comunicacion con Kokoro."""


def available(timeout=5):
    """Comprueba si Kokoro responde."""
    try:
        with urllib.request.urlopen(
            KOKORO_URL + "/v1/models",
            timeout=timeout
        ) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False



def _normalize_kokoro_wav(path):
    """Reescribe la cabecera WAV para registrar la duracion real."""
    import os
    import subprocess
    import tempfile
    from pathlib import Path

    original = Path(path)

    fd, temporary = tempfile.mkstemp(
        suffix=".wav",
        dir=str(original.parent),
    )
    os.close(fd)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-i", str(original),
                "-c:a", "pcm_s16le",
                temporary,
            ],
            check=True,
            timeout=120,
        )
        os.replace(temporary, original)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def generate(text, voice, output_path, speed=1.0, timeout=240):
    """Genera un WAV con Kokoro y devuelve sus metadatos."""

    if voice not in SPANISH_VOICES:
        raise ValueError("Voz Kokoro no permitida: " + voice)

    if not text or not text.strip():
        raise ValueError("El texto esta vacio")

    speed = float(speed)

    if not 0.5 <= speed <= 2.0:
        raise ValueError("Velocidad fuera del rango permitido")

    output_path = Path(output_path)

    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice,
        "response_format": "wav",
        "speed": speed,
    }

    request = urllib.request.Request(
        KOKORO_URL + "/v1/audio/speech",
        data=json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8"
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout
        ) as response:
            audio = response.read()

    except (urllib.error.URLError, TimeoutError) as exc:
        raise KokoroError(
            "No se pudo generar audio con Kokoro"
        ) from exc

    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        raise KokoroError("Respuesta WAV invalida")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(output_path, "wb") as file:
        file.write(audio)

    try:
        _normalize_kokoro_wav(output_path)
        with wave.open(str(output_path), "rb") as wav:
            duration = (
                wav.getnframes() / wav.getframerate()
            )
    except (wave.Error, EOFError, ZeroDivisionError) as exc:
        output_path.unlink(missing_ok=True)
        raise KokoroError(
            "El archivo WAV no es compatible"
        ) from exc

    return {
        "file": output_path.name,
        "duration": duration,
        "voice": voice,
        "speed": speed,
        "provider": "kokoro",
    }