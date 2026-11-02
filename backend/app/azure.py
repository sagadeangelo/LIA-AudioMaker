"""Azure Speech TTS para LIA AudioMaker."""

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path
from xml.sax.saxutils import escape


class AzureSpeechError(Exception):
    pass


def configuration():
    region = os.getenv("AZURE_SPEECH_REGION", "").strip()
    key = os.getenv("AZURE_SPEECH_KEY", "").strip()
    if not region or not key:
        raise AzureSpeechError("Azure Speech no esta configurado")
    return region, key


def voices():
    region, key = configuration()
    url = (
        f"https://{region}.tts.speech.microsoft.com"
        "/cognitiveservices/voices/list"
    )
    request = urllib.request.Request(
        url,
        headers={"Ocp-Apim-Subscription-Key": key},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AzureSpeechError(
            "No se pudo consultar el catalogo Azure"
        ) from exc


def generate(text, voice, speed, output_path):
    region, key = configuration()

    if not text or not text.strip():
        raise ValueError("Texto vacio")

    if not (
        voice.startswith("es-MX-")
        or voice.startswith("es-ES-")
    ):
        raise ValueError("Solo se permiten voces es-MX y es-ES")

    if not voice.endswith("Neural") or ":" in voice:
        raise ValueError("Voz Azure no admitida en esta fase")

    speed = float(speed)
    if not 0.5 <= speed <= 2.0:
        raise ValueError("Velocidad fuera de rango")

    locale = voice[:5]
    rate = round((speed - 1.0) * 100)

    ssml = (
        f'<speak version="1.0" '
        f'xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="{locale}">'
        f'<voice name="{escape(voice)}">'
        f'<prosody rate="{rate:+d}%">'
        f'{escape(text)}'
        f'</prosody></voice></speak>'
    )

    url = (
        f"https://{region}.tts.speech.microsoft.com"
        "/cognitiveservices/v1"
    )

    request = urllib.request.Request(
        url,
        data=ssml.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat":
                "riff-24khz-16bit-mono-pcm",
            "User-Agent": "LIA-AudioMaker",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        raise AzureSpeechError(
            f"Azure Speech respondio HTTP {exc.code}"
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AzureSpeechError(
            "No se pudo conectar con Azure Speech"
        ) from exc

    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        raise AzureSpeechError("Azure no devolvio un WAV valido")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        dir=str(output_path.parent)
    ) as directory:
        source = Path(directory) / "azure-original.wav"
        source.write_bytes(audio)

        subprocess.run(
            [
                "ffmpeg", "-nostdin", "-v", "error",
                "-i", str(source),
                "-c:a", "pcm_s16le",
                "-y", str(output_path),
            ],
            check=True,
            timeout=120,
        )

    with wave.open(str(output_path), "rb") as wav:
        duration = wav.getnframes() / wav.getframerate()

    return {
        "file": output_path.name,
        "duration": duration,
        "voice": voice,
        "speed": speed,
        "provider": "azure",
    }
