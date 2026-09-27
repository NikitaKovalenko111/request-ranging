
from pathlib import Path
from time import perf_counter

from sentence_transformers import SentenceTransformer

from .preprocess import clean_text
from .main import extract_keywords
from .skill_matching import run_matching


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BASE_DIR = PROJECT_ROOT / 'examples' / 'feature_extractor'

INPUT_FILE = BASE_DIR / "request.txt"
PROCESSED_FILE = BASE_DIR / "processed.txt"

MODEL_PATH = (
    PROJECT_ROOT
    / 'models'
    / 'feature-extractor'
    / 'matching'
    / 'models'
    / "paraphrase-multilingual-MiniLM-L12-v2"
)


def preprocess_request():
    """
    Читает request.txt, очищает текст
    и обновляет processed.txt.
    """
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Не найден файл: {INPUT_FILE}"
        )

    text = INPUT_FILE.read_text(encoding="utf-8")

    processed_text = clean_text(text)

    PROCESSED_FILE.write_text(
        processed_text,
        encoding="utf-8",
    )

    print(
        f"processed.txt обновлён: "
        f"{len(processed_text)} символов"
    )


def main():
    start = perf_counter()

    # 1. Обновляем processed.txt.
    print("\nЭТАП 1: Предварительная обработка")
    preprocess_request()

    # 2. Загружаем модель один раз.
    print("\nЭТАП 2: Загрузка модели")

    model = SentenceTransformer(
        str(MODEL_PATH),
        local_files_only=True,
    )

    # 3. Извлекаем ключевые фразы.
    print("\nЭТАП 3: Извлечение ключевых фраз")
    extract_keywords(model)

    # 4. Сопоставляем заявку с исполнителями.
    print("\nЭТАП 4: Skill Matching")
    run_matching(model)

    print(
        f"\nPipeline завершён за "
        f"{perf_counter() - start:.2f} сек."
    )


if __name__ == "__main__":
    main()
