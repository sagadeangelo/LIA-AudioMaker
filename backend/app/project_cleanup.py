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
