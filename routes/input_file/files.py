import hashlib
import os
from datetime import datetime

from flask import url_for


def ensure_upload_dir(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)


def is_allowed_extension(filename, config):
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext in config["allowed_exts"]


def is_safe_filename(filename):
    if not filename:
        return False
    if "/" in filename or "\\" in filename:
        return False
    if ".." in filename:
        return False
    if filename != os.path.basename(filename):
        return False
    return True


def format_size(size_bytes):
    size = float(size_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def compute_file_hash(path, config):
    hasher = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(config["hash_chunk_size"]), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_file_record(upload_dir, filename, config, existing=None, include_hash=True):
    existing = existing if isinstance(existing, dict) else None
    path = os.path.join(upload_dir, filename)
    size_bytes = os.path.getsize(path)
    modified_ts = os.path.getmtime(path)
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    is_image = ext in config["image_exts"]

    file_hash = None
    if existing and existing.get("size_bytes") == size_bytes and existing.get("modified_ts") == modified_ts and existing.get("hash"):
        file_hash = existing.get("hash")
    if include_hash and not file_hash:
        file_hash = compute_file_hash(path, config)

    return {
        "name": filename,
        "size_bytes": size_bytes,
        "modified_ts": modified_ts,
        "hash": file_hash,
        "ext": ext,
        "is_image": is_image,
    }


def build_file_meta(record, course_id, uuid_for_upload, config):
    filename = record.get("name", "")
    size_bytes = record.get("size_bytes", 0)
    ext = record.get("ext") or os.path.splitext(filename)[1].lstrip(".").lower()
    is_image = record.get("is_image", ext in config["image_exts"])
    modified_ts = record.get("modified_ts", 0)
    modified = datetime.fromtimestamp(modified_ts).strftime("%Y-%m-%d %H:%M") if modified_ts else ""

    preview_url = url_for("input_file.get_file", filename=filename, course=course_id, uuid_for_upload=uuid_for_upload)
    download_url = url_for("input_file.download_file", filename=filename, course=course_id, uuid_for_upload=uuid_for_upload)
    file_hash = record.get("hash")

    return {
        "name": filename,
        "size_bytes": size_bytes,
        "size_label": format_size(size_bytes),
        "ext": ext or "file",
        "modified": modified,
        "modified_ts": modified_ts,
        "is_image": is_image,
        "preview_url": preview_url if is_image else None,
        "download_url": download_url,
        "hash": file_hash,
        "hash_short": file_hash[:12] if file_hash else None,
    }
