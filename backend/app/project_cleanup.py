from pathlib import Path


def project_files(project):
    """Collect source manuscript and active/historical audio filenames."""
    names = set()

    source = project.get("source_file")
    if source:
        names.add(source)

    for chapter in project.get("chapters", []):
        for segment in chapter.get("segments", []):
            audio = segment.get("audio")
            if audio:
                names.add(audio)

            for version in segment.get("versions", []):
                filename = version.get("file")
                if filename:
                    names.add(filename)

    for sound in project.get("sound_effects", []):
        if sound.get("file"):
            names.add(sound["file"])

    for mix in project.get("sound_mixes", []) + project.get("sound_project_mixes", []):
        if mix.get("file"):
            names.add(mix["file"])
        for profile in mix.get("mp3_profiles", {}).values():
            if profile.get("file"):
                names.add(profile["file"])
        if mix.get("mp3_file"):
            names.add(mix["mp3_file"])

    for item in list(project.get("sound_scene_previews", {}).values()) + project.get("sound_scene_preview_history", []) + project.get("sound_scene_exports", []):
        if item.get("file"):
            names.add(item["file"])
    for item in project.get("sound_scene_exports", []) + project.get("sound_project_mixes", []):
        for source in item.get("sources", {}).values():
            if source.get("file"):
                names.add(source["file"])
    for plan in project.get("production_plans", []):
        for split in plan.get("splits", []):
            original = split.get("original", {})
            if original.get("audio"):
                names.add(original["audio"])
            for version in original.get("versions", []):
                if version.get("file"):
                    names.add(version["file"])
    for run in project.get("production_runs", []):
        for k in ("file", "mp3_file"):
            if run.get(k):names.add(run[k])
        for clip in run.get("clips", {}).values():
            if clip.get("file"):names.add(clip["file"])
        for original in run.get("backups", []):
            if original.get("audio"):names.add(original["audio"])
            for version in original.get("versions", []):
                if version.get("file"):names.add(version["file"])
    return names


def safe_file(data_dir, filename):
    """Return a validated direct child of the audio directory."""
    if not isinstance(filename, str):
        return None

    if not filename or Path(filename).name != filename:
        return None

    if filename in (".", "..") or chr(92) in filename:
        return None

    root = Path(data_dir).resolve()
    target = root / filename

    if target.is_symlink():
        return None

    if target.resolve().parent != root:
        return None

    return target


def exclusive_files(project, other_projects):
    """Files belonging to this project and not referenced elsewhere."""
    own = project_files(project)

    shared = set()
    for other in other_projects:
        shared.update(project_files(other))

    return own - shared


def cleanup_files(data_dir, filenames):
    """Delete only validated filenames; return failures for retry."""
    deleted = []
    failed = []

    for filename in sorted(set(filenames)):
        path = safe_file(data_dir, filename)

        if path is None:
            failed.append(filename)
            continue

        try:
            path.unlink(missing_ok=True)
            deleted.append(filename)
        except OSError:
            failed.append(filename)

    return {"deleted": deleted, "failed": failed}
