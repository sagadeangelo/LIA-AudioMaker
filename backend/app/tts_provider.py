"""Seleccion de motores TTS para LIA AudioMaker."""

from . import azure, kokoro


KOKORO_VOICES = frozenset({
    "em_santa",
    "em_alex",
    "ef_dora",
})

DEFAULT_VOICE = "em_santa"
DEFAULT_SPEED = 1.0


def is_azure_voice(voice):
    return (
        isinstance(voice, str)
        and voice.startswith(("es-MX-", "es-ES-"))
        and voice.endswith("Neural")
        and ":" not in voice
    )


def provider_for_voice(voice):
    if voice in KOKORO_VOICES:
        return "kokoro"

    if is_azure_voice(voice):
        return "azure"

    raise ValueError("Voz TTS no compatible: " + str(voice))


def normalize_speed(voice, speed):
    provider_for_voice(voice)

    value = float(speed)

    if not 0.5 <= value <= 2.0:
        raise ValueError(
            "La velocidad debe estar entre 0.5 y 2.0"
        )

    return value


def generate(text, voice, speed, output_path):
    provider = provider_for_voice(voice)
    speed = normalize_speed(voice, speed)

    if provider == "kokoro":
        return kokoro.generate(
            text=text,
            voice=voice,
            speed=speed,
            output_path=output_path,
        )

    return azure.generate(
        text=text,
        voice=voice,
        speed=speed,
        output_path=output_path,
    )


def catalog():
    azure_voices = []
    azure_available = False

    try:
        raw = azure.voices()
        azure_voices = sorted({
            item["ShortName"]
            for item in raw
            if item.get("Locale") in ("es-MX", "es-ES")
            and is_azure_voice(item.get("ShortName"))
        })
        azure_available = True
    except (azure.AzureSpeechError, ValueError, KeyError):
        pass

    return {
        "default_provider": "kokoro",
        "providers": {
            "kokoro": {
                "available": kokoro.available(),
                "voices": sorted(KOKORO_VOICES),
            },
            "azure": {
                "available": azure_available,
                "voices": azure_voices,
            },
        },
    }
