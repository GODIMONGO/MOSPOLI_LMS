import hashlib
import json
import os
import xml.etree.ElementTree as ET

from config import patch


def repaint_svg(file_path, new_color, output_dir=None, castom_autput_path=False):
    if not castom_autput_path or not output_dir:
        output_dir = os.path.join(patch, "lib", "repainted_svgs")

    # ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # читаем содержимое файла
    with open(file_path, "rb") as f:
        content = f.read()

    # считаем уникальный хэш содержания
    file_hash = hashlib.md5(content).hexdigest()

    # путь к базе обработанных файлов
    db_dir = os.path.join(patch, "lib", "processed_svg")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "processed_svgs.json")

    # создаём / читаем базу
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            try:
                db = json.load(f)
            except Exception:
                db = {}
    else:
        db = {}

    # Формируем путь, который должен быть у файла
    output_path = os.path.join(output_dir, f"{file_hash}.svg")

    # ----- проверяем, обрабатывали ли именно ЭТУ картинку -----
    if file_hash in db:
        # но если файла вдруг нет — пересоздаём
        if os.path.exists(db[file_hash]):
            return db[file_hash]

    # ----- если нет или файл утерян — создаём новый -----
    try:
        tree = ET.fromstring(content)
    except TypeError:
        tree = ET.fromstring(content.decode("utf-8"))

    root = tree

    for elem in root.iter():
        if "stroke" in elem.attrib:
            elem.set("stroke", new_color)
        if "fill" in elem.attrib and elem.attrib.get("fill") not in ("none", "transparent"):
            elem.set("fill", new_color)

    # сохраняем результат (write with xml declaration and utf-8)
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)

    # обновляем запись в базе
    db[file_hash] = output_path
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    return output_path
