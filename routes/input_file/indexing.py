import json
import os

import dramatiq
from loguru import logger

from .config import load_input_file_config
from .files import build_file_meta, build_file_record, ensure_upload_dir, is_safe_filename


def load_index(upload_dir, upload_index):
    ensure_upload_dir(upload_dir)
    if not os.path.isfile(upload_index):
        return {}
    try:
        with open(upload_index, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}
    files_data = data.get("files")
    if isinstance(files_data, dict):
        return files_data
    return data


def save_index(upload_dir, upload_index, index):
    ensure_upload_dir(upload_dir)
    temp_path = f"{upload_index}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump({"files": index}, file, ensure_ascii=True, indent=2)
    os.replace(temp_path, upload_index)


def sync_upload_index(upload_dir, upload_index, config, include_hash=True):
    ensure_upload_dir(upload_dir)
    index = load_index(upload_dir, upload_index)
    changed = False

    if not index:
        for filename in os.listdir(upload_dir):
            if filename.startswith("."):
                continue
            path = os.path.join(upload_dir, filename)
            if not os.path.isfile(path) or not is_safe_filename(filename):
                continue
            index[filename] = build_file_record(upload_dir, filename, config, include_hash=include_hash)
            changed = True
    else:
        for filename in list(index.keys()):
            if not is_safe_filename(filename):
                index.pop(filename, None)
                changed = True
                continue
            path = os.path.join(upload_dir, filename)
            if not os.path.isfile(path):
                index.pop(filename, None)
                changed = True
                continue
            record = build_file_record(upload_dir, filename, config, index.get(filename), include_hash=include_hash)
            if record != index.get(filename):
                index[filename] = record
                changed = True

    if changed:
        save_index(upload_dir, upload_index, index)
    return index


def list_uploaded_files(upload_dir, upload_index, course_id, uuid_for_upload, config):
    index = sync_upload_index(upload_dir, upload_index, config, include_hash=False)

    entries = []
    for filename, record in index.items():
        if not is_safe_filename(filename):
            continue
        if record.get("name") != filename:
            record = {**record, "name": filename}
        entries.append(build_file_meta(record, course_id, uuid_for_upload, config))

    entries.sort(key=lambda item: item["modified_ts"], reverse=True)
    for item in entries:
        item.pop("modified_ts", None)
    return entries


@dramatiq.actor(queue_name="input_file")
def sync_upload_index_actor(uuid_for_upload: str, upload_dir: str, upload_index: str):
    config = load_input_file_config(uuid_for_upload)
    if config is None:
        logger.warning(f"sync_upload_index_actor: не найден конфиг для uuid_for_upload={uuid_for_upload}")
        return
    sync_upload_index(upload_dir, upload_index, config)


def enqueue_index_sync(uuid_for_upload, upload_dir, upload_index):
    try:
        sync_upload_index_actor.send(uuid_for_upload, upload_dir, upload_index)
    except Exception as enqueue_error:
        logger.warning(f"Не удалось отправить задачу sync_upload_index_actor: {enqueue_error}")
