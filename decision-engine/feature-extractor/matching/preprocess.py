
import re
from typing import List, Dict


# Заголовки вида:
# 1. РЕГИСТРАЦИЯ И УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# 2. ИНТЕГРАЦИЯ С ВНЕШНИМИ СИСТЕМАМИ
HEADING_PATTERN = re.compile(
    r"(?m)^\s*(\d+\.\s+[А-ЯЁA-Z][^\n]*)\s*$"
)


def clean_text(text: str) -> str:
    """
    Безопасная очистка текста.
    Не удаляет слова и предложения.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def split_into_sections(text: str) -> List[Dict[str, str]]:
    """
    Разбивает документ по нумерованным заголовкам.

    Текст до первого заголовка сохраняется
    как introduction.
    """
    text = clean_text(text)

    matches = list(HEADING_PATTERN.finditer(text))
    sections = []

    # Если заголовков нет, сохраняем весь текст одним блоком.
    if not matches:
        if text:
            sections.append({
                "title": "document",
                "text": text
            })
        return sections

    # Вводная часть до первого заголовка.
    introduction = text[:matches[0].start()].strip()

    if introduction:
        sections.append({
            "title": "introduction",
            "text": introduction
        })

    # Извлекаем содержимое каждого раздела.
    for i, match in enumerate(matches):
        title = match.group(1).strip()

        start = match.end()
        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(text)
        )

        section_text = text[start:end].strip()

        if section_text:
            sections.append({
                "title": title,
                "text": section_text
            })

    return sections