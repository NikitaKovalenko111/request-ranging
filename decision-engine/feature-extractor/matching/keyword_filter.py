
import re
from typing import Any


# Фразы, которые обычно не описывают конкретную технологию,
# навык или предметную область.
GENERIC_PHRASES = {
    "основная цель",
    "цель проекта",
    "задачи проекта",
    "данного проекта",
    "в рамках проекта",
    "информационная система",
    "программное обеспечение",
    "цифровая платформа",
    "основные требования",
    "система должна",
    "необходимо реализовать",
    "следует предусмотреть",
    "осуществление процесса",
    "обеспечение возможности",
}


def normalize_phrase(phrase: str) -> str:
    """Нормализует фразу для сравнения."""
    phrase = phrase.lower().strip()
    phrase = re.sub(r"[^\w\s+#./-]", "", phrase)
    phrase = re.sub(r"\s+", " ", phrase)
    return phrase


def is_valid_keyword(phrase: str) -> bool:
    """Проверяет, стоит ли сохранять ключевую фразу."""
    normalized = normalize_phrase(phrase)

    if not normalized:
        return False

    if len(normalized) < 3:
        return False

    if normalized in GENERIC_PHRASES:
        return False

    words = normalized.split()

    # Отсекаем одиночные слишком общие слова.
    if len(words) == 1 and normalized in {
        "система",
        "проект",
        "задача",
        "пользователь",
        "процесс",
        "работа",
        "данные",
        "решение",
        "разработка",
        "обеспечение",
    }:
        return False

    return True


def merge_keywords(
    sections: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Объединяет точные дубликаты ключевых фраз
    из разных разделов.
    """
    merged = {}

    for section in sections:
        section_title = section["section_title"]

        for keyword in section["keywords"]:
            phrase = keyword["phrase"]
            weight = float(keyword["weight"])

            if not is_valid_keyword(phrase):
                continue

            normalized = normalize_phrase(phrase)

            if normalized not in merged:
                merged[normalized] = {
                    "phrase": phrase,
                    "normalized": normalized,
                    "weight": weight,
                    "sections": [section_title],
                }
            else:
                item = merged[normalized]

                # Сохраняем максимальный вес.
                item["weight"] = max(item["weight"], weight)

                if section_title not in item["sections"]:
                    item["sections"].append(section_title)

    result = list(merged.values())

    result.sort(
        key=lambda item: item["weight"],
        reverse=True
    )

    return result