import json
import os
import re

from loguru import logger

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _normalize_exts(values, fallback):
    if not isinstance(values, list):
        values = fallback
    prepared = {str(ext).strip().lstrip(".").lower() for ext in values if str(ext).strip()}
    return prepared or set(fallback)


def _to_positive_int(value, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


def fetch_input_file_config_from_db(uuid_for_upload: str):
    default_input_file_config = {
        "test": {
            "uploads_root": "uploads",
            "image_exts": ["jpg", "jpeg", "png", "gif"],
            "allowed_exts": ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt"],
            "max_file_size_mb": 500,
            "max_attached_files": 20,
            "hash_chunk_size": 1048576,
            "course_id": "test",
            "course_id_pattern": "^[a-zA-Z0-9_-]+$",
        }
    }
    return default_input_file_config.get(uuid_for_upload)


def load_input_file_config(uuid_for_upload: str):
    config = fetch_input_file_config_from_db(uuid_for_upload)
    if config is None:
        return None
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError as error:
            logger.warning(f"Некорректный JSON конфига из БД: {error}")
            return None
    if not isinstance(config, dict):
        return None

    uploads_root_raw = config.get("uploads_root", "uploads")
    uploads_root_name = uploads_root_raw.strip() if isinstance(uploads_root_raw, str) else "uploads"
    uploads_root_name = uploads_root_name or "uploads"

    image_exts = _normalize_exts(config.get("image_exts"), ["jpg", "jpeg", "png", "gif"])
    allowed_exts = _normalize_exts(config.get("allowed_exts"), ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt"])

    max_file_size_mb = _to_positive_int(config.get("max_file_size_mb"), 500)
    max_attached_files = _to_positive_int(config.get("max_attached_files"), 20)
    hash_chunk_size = _to_positive_int(config.get("hash_chunk_size"), 1024 * 1024)

    course_id_raw = config.get("course_id", "default")
    course_id = course_id_raw.strip() if isinstance(course_id_raw, str) else "default"
    course_id = course_id or "default"

    course_id_pattern_raw = config.get("course_id_pattern", r"^[a-zA-Z0-9_-]+$")
    course_id_pattern = course_id_pattern_raw if isinstance(course_id_pattern_raw, str) else r"^[a-zA-Z0-9_-]+$"
    try:
        course_id_re = re.compile(course_id_pattern)
    except re.error:
        course_id_re = re.compile(r"^[a-zA-Z0-9_-]+$")

    uploads_root = uploads_root_name if os.path.isabs(uploads_root_name) else os.path.join(APP_ROOT, uploads_root_name)

    return {
        "uploads_root": uploads_root,
        "image_exts": image_exts,
        "allowed_exts": allowed_exts,
        "max_file_size_mb": max_file_size_mb,
        "max_file_size_bytes": max_file_size_mb * 1024 * 1024,
        "max_attached_files": max_attached_files,
        "hash_chunk_size": hash_chunk_size,
        "course_id": course_id,
        "course_id_re": course_id_re,
    }
