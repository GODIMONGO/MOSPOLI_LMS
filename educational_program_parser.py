import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pdfplumber


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_line(value: str) -> str:
    return _normalize_spaces(value.replace("\u00a0", " "))


def _extract_pdf_text(pdf_path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append((page.extract_text() or "").replace("\r", ""))
    return "\n".join(pages)


def _extract_section(text: str, start_re: str, end_re: str) -> str:
    match = re.search(start_re + r"(.*?)" + end_re, text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""


def _extract_metadata(text: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    patterns = {
        "discipline_name": r"Дисциплина\s+«([^»]+)»",
        "direction": r"Направление подготовки\s*\n\s*([^\n]+)",
        "profile": r"Профиль\s*\n\s*([^\n]+)",
        "qualification": r"Квалификация\s*\n\s*([^\n]+)",
        "study_forms": r"Формы обучения\s*\n\s*([^\n]+)",
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            metadata[field] = _normalize_line(match.group(1))
    workload = re.search(
        r"Общая трудоемкость дисциплины составляет\s*_*([0-9]+)_*\s*зачетных.*?\(_*([0-9]+)_*\s*часов\)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if workload:
        metadata["credits"] = int(workload.group(1))
        metadata["total_hours"] = int(workload.group(2))
    return metadata


def _extract_competencies(text: str) -> list[dict[str, Any]]:
    section = _extract_section(text, r"Код и наименование компетенций", r"2\s+Место дисциплины")
    if not section:
        return []
    competencies: list[dict[str, Any]] = []
    raw_matches = list(re.finditer(r"(?:^|\s)((?:УК|ОПК|ПК)-\d+)\.", section, flags=re.MULTILINE))
    code_matches: list[re.Match[str]] = []
    for match in raw_matches:
        left = match.start(1) - 1
        while left >= 0 and section[left].isspace():
            left -= 1
        if left >= 0 and section[left] in {"И", "и"}:
            continue
        code_matches.append(match)

    for index, match in enumerate(code_matches):
        code_start = match.start(1)
        code_end = match.end(1) + 1
        next_start = code_matches[index + 1].start(1) if index + 1 < len(code_matches) else len(section)
        block = section[code_start:next_start]
        code = match.group(1)
        after_code = block[code_end - code_start :]

        indicator_start = re.search(r"И(УК|ОПК|ПК)-\d+\.\d+\.", after_code)
        if indicator_start:
            name_part = after_code[: indicator_start.start()]
            indicators_part = after_code[indicator_start.start() :]
        else:
            name_part = after_code
            indicators_part = ""

        indicator_entries: list[dict[str, str]] = []
        indicator_matches = list(re.finditer(r"(И(?:УК|ОПК|ПК)-\d+\.\d+)\.", indicators_part))
        for indicator_index, indicator_match in enumerate(indicator_matches):
            indicator_start_pos = indicator_match.end()
            indicator_end_pos = (
                indicator_matches[indicator_index + 1].start() if indicator_index + 1 < len(indicator_matches) else len(indicators_part)
            )
            indicator_description = _normalize_line(indicators_part[indicator_start_pos:indicator_end_pos])
            indicator_entries.append({"code": indicator_match.group(1), "description": indicator_description})

        competencies.append(
            {
                "code": code,
                "name": _normalize_line(name_part).rstrip(","),
                "indicators": indicator_entries,
            }
        )
    return competencies


def _parse_thematic_rows(section: str) -> list[dict[str, Any]]:
    lines = [_normalize_line(line) for line in section.splitlines() if _normalize_line(line)]
    raw_rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        if line.startswith("Итого"):
            break
        if re.match(r"^\d+\s", line):
            if current:
                raw_rows.append(current)
            row_match = re.match(r"^(?P<number>\d+)\s+(?P<title>.+?)\s+(?P<hours>\d+(?:\s+\d+){2,5})$", line)
            if row_match:
                current = {
                    "number": int(row_match.group("number")),
                    "title_parts": [row_match.group("title")],
                    "hours": [int(item) for item in row_match.group("hours").split()],
                    "raw_parts": [line],
                }
            else:
                current = {"number": None, "title_parts": [], "hours": None, "raw_parts": [line]}
            continue
        if current and not re.match(r"^[0-9]+$", line):
            if not re.search(r"(Трудоемкость|Разделы/темы|дисциплины|Аудиторная работа|Лекции|Самостоятельная)", line):
                current["raw_parts"].append(line)
                if current["hours"] is not None:
                    current["title_parts"].append(line)
    if current:
        raw_rows.append(current)

    parsed_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        if row["number"] is None or row["hours"] is None:
            joined = " ".join(row["raw_parts"])
            match = re.match(r"^(?P<number>\d+)\s+(?P<title>.+?)\s+(?P<hours>\d+(?:\s+\d+){2,5})$", joined)
            if not match:
                continue
            number = int(match.group("number"))
            title = _normalize_line(match.group("title")).rstrip(".")
            hours = [int(item) for item in match.group("hours").split()]
        else:
            number = int(row["number"])
            title = _normalize_line(" ".join(row["title_parts"])).rstrip(".")
            hours = row["hours"]

        item: dict[str, Any] = {
            "topic_number": number,
            "title": title,
            "hours_raw": hours,
        }
        if len(hours) >= 1:
            item["total"] = hours[0]
        if len(hours) == 4:
            item["lectures"] = hours[1]
            item["labs_or_practice"] = hours[2]
            item["self_study"] = hours[3]
        elif len(hours) == 3:
            item["lectures"] = hours[1]
            item["self_study"] = hours[2]
        parsed_rows.append(item)
    return parsed_rows


def _extract_thematic_plan(text: str) -> dict[str, list[dict[str, Any]]]:
    full_time_section = _extract_section(
        text,
        r"3\.2\.1\s+Очная форма обучения",
        r"3\.3\s+Виды учебной работы",
    )
    part_time_section = _extract_section(
        text,
        r"3\.2\.1\s+Заочная форма обучения",
        r"3\.5\s+Содержание дисциплины",
    )
    return {"очная": _parse_thematic_rows(full_time_section), "заочная": _parse_thematic_rows(part_time_section)}


def _extract_topics(text: str) -> list[dict[str, Any]]:
    section = _extract_section(text, r"3\.5\s+Содержание дисциплины", r"3\.6")
    topic_matches = list(re.finditer(r"Тема\s+(\d+)\.\s*(.*?)(?=Тема\s+\d+\.|$)", section, flags=re.DOTALL | re.IGNORECASE))
    topics: list[dict[str, Any]] = []
    for topic_match in topic_matches:
        topic_number = int(topic_match.group(1))
        block = topic_match.group(2).strip()
        lines = [_normalize_line(line) for line in block.splitlines() if _normalize_line(line)]
        if not lines:
            topics.append({"topic_number": topic_number, "title": "", "description": ""})
            continue
        title = lines[0].rstrip(".")
        description = _normalize_line(" ".join(lines[1:])) if len(lines) > 1 else ""
        topics.append({"topic_number": topic_number, "title": title, "description": description})
    return topics


def _extract_labs(text: str) -> list[dict[str, Any]]:
    section = _extract_section(text, r"3\.6\.2\s+Лабораторные занятия", r"3\.7\.")
    lab_matches = list(re.finditer(r"ЛР-(\d+)\s+(.*?)(?=ЛР-\d+\s+|$)", section, flags=re.DOTALL | re.IGNORECASE))
    labs: list[dict[str, Any]] = []
    for lab_match in lab_matches:
        number = int(lab_match.group(1))
        raw_block = lab_match.group(2).strip()

        title_part = raw_block.split("Цель выполнения лабораторной работы:", maxsplit=1)[0]
        title = _normalize_line(title_part).rstrip(".")

        objective_match = re.search(
            r"Цель выполнения лабораторной работы:\s*(.*?)(?=Результат:|$)",
            raw_block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        result_match = re.search(r"Результат:\s*(.*)$", raw_block, flags=re.DOTALL | re.IGNORECASE)

        objective = _normalize_line(objective_match.group(1)) if objective_match else ""
        result = _normalize_line(result_match.group(1)) if result_match else ""
        objective = re.sub(r"\s+\d{1,2}$", "", objective).strip()
        result = re.sub(r"\s+\d{1,2}$", "", result).strip()

        labs.append(
            {
                "topic_number": number,
                "title": title,
                "objective": objective,
                "result": result,
            }
        )
    return labs


def _build_constructor_seed(
    topics: list[dict[str, Any]],
    labs: list[dict[str, Any]],
    thematic_plan: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    labs_map = {item["topic_number"]: item for item in labs}
    full_time_map = {item["topic_number"]: item for item in thematic_plan.get("очная", [])}
    part_time_map = {item["topic_number"]: item for item in thematic_plan.get("заочная", [])}

    seed_topics: list[dict[str, Any]] = []
    for topic in sorted(topics, key=lambda x: x["topic_number"]):
        number = topic["topic_number"]
        topic_lab = labs_map.get(number)
        full_time_hours = full_time_map.get(number, {})
        part_time_hours = part_time_map.get(number, {})

        blocks: list[dict[str, Any]] = [
            {
                "catalog_id": "theory",
                "title": "Информация",
                "content": {
                    "topic_number": number,
                    "topic_title": topic["title"],
                    "description": topic["description"],
                    "hours": {
                        "очная": full_time_hours.get("hours_raw", []),
                        "заочная": part_time_hours.get("hours_raw", []),
                    },
                },
            }
        ]

        if topic_lab:
            blocks.append(
                {
                    "catalog_id": "assignment",
                    "title": "Лабораторная работа",
                    "content": {
                        "name": topic_lab.get("title", ""),
                        "objective": topic_lab.get("objective", ""),
                        "result": topic_lab.get("result", ""),
                    },
                }
            )

        blocks.append(
            {
                "catalog_id": "quiz",
                "title": "Проверка знаний",
                "content": {
                    "hint": "Добавьте контрольные вопросы по теме.",
                },
            }
        )

        seed_topics.append(
            {
                "topic_number": number,
                "title": topic["title"],
                "blocks": blocks,
            }
        )
    return seed_topics


def parse_educational_program(pdf_path: Path) -> dict[str, Any]:
    text = _extract_pdf_text(pdf_path)
    metadata = _extract_metadata(text)
    competencies = _extract_competencies(text)
    thematic_plan = _extract_thematic_plan(text)
    topics = _extract_topics(text)
    labs = _extract_labs(text)
    constructor_seed = _build_constructor_seed(topics, labs, thematic_plan)

    return {
        "source_file": str(pdf_path),
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "course": metadata,
        "competencies": competencies,
        "thematic_plan": thematic_plan,
        "topics": topics,
        "labs": labs,
        "constructor_seed": constructor_seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Парсер рабочей программы дисциплины в JSON для конструктора курса.")
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("B1.1.7_Osnovy_programmirovaniya(4).pdf"),
        help="Путь к входному PDF.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("educational_program_for_constructor.json"),
        help="Путь для выходного JSON.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Файл не найден: {args.input}")

    payload = parse_educational_program(args.input)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
