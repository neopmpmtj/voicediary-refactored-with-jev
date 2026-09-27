import re
from pathlib import Path

from django.conf import settings

ATTACHMENTS_SUBDIR = "attachments"
ARTIFACTS_SUBDIR = "artifacts"


def sanitize_storage_filename(name):
    if not name or not str(name).strip():
        return "uploaded_file"
    safe = re.sub(r"[^\w.\- ]", "", str(name).strip())
    if not safe:
        return "uploaded_file"
    if len(safe) <= 200:
        return safe
    dot_pos = safe.rfind(".")
    if dot_pos > 0:
        ext = safe[dot_pos:]
        stem = safe[:dot_pos]
        return stem[: 200 - len(ext)] + ext
    return safe[:200]


def allocate_unique_attachment_filename(directory, safe_name, used):
    base = (safe_name or "").strip() or "uploaded_file"
    path_from = Path(base)
    stem = path_from.stem or "file"
    suffix = path_from.suffix
    candidate = base
    n = 1
    while candidate in used or (directory / candidate).exists():
        if suffix:
            candidate = f"{stem}_{n}{suffix}"
        else:
            candidate = f"{stem}_{n}"
        n += 1
        if n > 10_000:
            raise OSError(f"Could not allocate unique filename for {safe_name!r}")
    used.add(candidate)
    return candidate


def attachments_dir_for_entry(user_id, entry_id):
    folder = Path(settings.MEDIA_ROOT) / ATTACHMENTS_SUBDIR / str(user_id) / str(entry_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def artifacts_dir_for_user(user_id):
    folder = Path(settings.MEDIA_ROOT) / ARTIFACTS_SUBDIR / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def attachment_disk_path(relative_path):
    return Path(settings.MEDIA_ROOT) / relative_path


def attachment_path_is_allowed(user_id, relative_path):
    root = (Path(settings.MEDIA_ROOT) / ATTACHMENTS_SUBDIR / str(user_id)).resolve()
    try:
        path = attachment_disk_path(relative_path).resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return False
    return path.is_file()
