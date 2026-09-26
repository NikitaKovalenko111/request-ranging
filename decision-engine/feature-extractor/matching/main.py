
import json
from pathlib import Path

from keybert import KeyBERT

from preprocess import split_into_sections
from keyword_filter import merge_keywords, is_valid_keyword


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "processed.txt"
OUTPUT_FILE = BASE_DIR / "result.json"

TOP_N = 10
NGRAM_RANGE = (1, 3)


def extract_keywords(model):
    """
    Извлекает ключевые фразы с использованием
    уже загруженной SentenceTransformer модели.
    """

    text = INPUT_FILE.read_text(encoding="utf-8")
    sections = split_into_sections(text)

    print(f"Найдено разделов: {len(sections)}")

    # Передаём готовую модель в KeyBERT.
    kw_model = KeyBERT(model=model)

    section_results = []

    for index, section in enumerate(sections, start=1):
        title = section["title"]
        section_text = section["text"]

        print(
            f"[{index}/{len(sections)}] "
            f"Обрабатывается: {title}"
        )

        keywords = kw_model.extract_keywords(
            section_text,
            keyphrase_ngram_range=NGRAM_RANGE,
            stop_words=None,
            top_n=TOP_N,
            use_mmr=True,
            diversity=0.5,
        )

        filtered_keywords = [
            {
                "phrase": phrase,
                "weight": round(float(score), 4),
            }
            for phrase, score in keywords
            if is_valid_keyword(phrase)
        ]

        section_results.append({
            "section_title": title,
            "keywords": filtered_keywords,
        })

    merged_keywords = merge_keywords(section_results)

    output = {
        "sections_count": len(section_results),
        "keywords_count": len(merged_keywords),
        "sections": section_results,
        "keywords": merged_keywords,
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Уникальных фраз: {len(merged_keywords)}")
    print(f"Результат сохранён: {OUTPUT_FILE}")

    return output