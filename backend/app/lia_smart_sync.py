import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from app import sound_mixer as sm

PID = "6bda4ac5-e78c-4240-89a4-ca44bac8f5fe"
SCENE_ID = "de7e7a15-aab7-4820-95a4-d65775da04a4"
SEGMENT_ID = "f5f0e514-92b5-4290-9f6c-4ce4d8ca3c09"
PHRASE = "se escuchaban como si estuviesen excavando"

def norm(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text)

def find_phrase(words, phrase):
    target = norm(phrase)
    expected_count = len(phrase.split())
    candidates = []

    for i in range(len(words)):
        for size in range(max(1, expected_count-2), expected_count+3):
            chunk = words[i:i+size]
            if len(chunk) != size:
                continue

            spoken = "".join(norm(w.word) for w in chunk)
            score = SequenceMatcher(None, target, spoken).ratio()

            candidates.append((score, chunk))

    if not candidates:
        return None

    score, chunk = max(candidates, key=lambda x: x[0])

    return {
        "similarity": round(score, 3),
        "start": round(chunk[0].start, 3),
        "end": round(chunk[-1].end, 3),
        "recognized": " ".join(w.word.strip() for w in chunk)
    }

def main():
    from faster_whisper import WhisperModel

    project = sm.main().get(PID)
    scene = sm.scene_by_id(project, SCENE_ID)

    segment = next(
        s for s in sm.source_segments(project, scene)
        if s["id"] == SEGMENT_ID
    )

    audio = sm.wav_info(sm.approved_audio(segment))
    if not audio:
        raise RuntimeError("No existe audio aprobado.")

    timeline = next(
        s for s in scene["segments"]
        if s["id"] == SEGMENT_ID
    )

    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8",
        cpu_threads=4
    )

    import subprocess
    import numpy as np

    # Decodificar el WAV con FFmpeg para evitar incompatibilidades de PyAV.
    decoded = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-nostdin", "-i", str(audio["path"]),
            "-f", "f32le", "-ac", "1", "-ar", "16000", "-"
        ],
        capture_output=True,
        check=True
    )

    samples = np.frombuffer(decoded.stdout, dtype=np.float32).copy()

    if samples.size == 0:
        raise RuntimeError("El WAV no contiene muestras de audio.")

    chunks, info = model.transcribe(
        samples,
        language="es",
        word_timestamps=True,
        vad_filter=False,
        beam_size=5
    )

    words = [
        word
        for chunk in chunks
        for word in (chunk.words or [])
        if word.start is not None and word.end is not None
    ]

    match = find_phrase(words, PHRASE)

    result = {
        "phrase": PHRASE,
        "recognized_text": " ".join(w.word.strip() for w in words),
        "match": match,
        "status": "requires_review"
    }

    if match:
        result["scene_seconds"] = round(
            timeline["offset"] + match["start"], 3
        )
        result["segment_offset"] = match["start"]

    output = Path("/tmp/LIA_SMART_SYNC_SILVANO.json")
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
