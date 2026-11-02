from pathlib import Path


def build_audio_library(project: dict, data_dir: Path) -> dict:
    """Construye un inventario de solo lectura desde el proyecto persistido."""

    chapters = []
    totals = {
        "segments": 0,
        "generated": 0,
        "missing": 0,
        "pending": 0,
        "excluded": 0,
        "review": 0,
        "chapters_ready": 0,
    }

    for chapter_index, chapter in enumerate(project.get("chapters", []), 1):
        items = []
        included_count = 0
        ready_count = 0

        for segment_index, segment in enumerate(chapter.get("segments", []), 1):
            audio = segment.get("audio")
            excluded = bool(segment.get("excluded"))
            separator = bool(segment.get("is_separator"))
            review = bool(segment.get("review"))

            exists = bool(
                audio
                and Path(audio).name == audio
                and (data_dir / audio).is_file()
            )

            if excluded or separator:
                status = "excluded"
                totals["excluded"] += 1
            elif audio and exists:
                status = "generated"
                totals["generated"] += 1
                ready_count += 1
            elif audio and not exists:
                status = "missing"
                totals["missing"] += 1
            elif review:
                status = "review"
                totals["review"] += 1
            else:
                status = "pending"
                totals["pending"] += 1

            if not excluded and not separator:
                included_count += 1

            totals["segments"] += 1

            versions = []

            for version in segment.get("versions", []):
                filename = version.get("file")

                versions.append({
                    "file": filename,
                    "exists": bool(
                        filename
                        and Path(filename).name == filename
                        and (data_dir / filename).is_file()
                    ),
                    "voice": version.get("voice"),
                    "speed": version.get("speed"),
                    "provider": version.get("provider"),
                })

            items.append({
                "id": segment.get("id"),
                "number": segment_index,
                "speaker": segment.get("speaker"),
                "voice": segment.get("voice"),
                "speed": segment.get("speed", 1.0),
                "text": segment.get("text", ""),
                "audio": audio,
                "duration": segment.get("duration", 0),
                "status": status,
                "review": review,
                "excluded": excluded,
                "versions": versions,
            })

        ready = included_count > 0 and included_count == ready_count

        if ready:
            totals["chapters_ready"] += 1

        chapters.append({
            "id": chapter.get("id"),
            "number": chapter_index,
            "title": chapter.get("title", ""),
            "included": included_count,
            "generated": ready_count,
            "ready": ready,
            "segments": items,
        })

    return {
        "project_id": project.get("id"),
        "title": project.get("title"),
        "totals": totals,
        "chapters": chapters,
    }
