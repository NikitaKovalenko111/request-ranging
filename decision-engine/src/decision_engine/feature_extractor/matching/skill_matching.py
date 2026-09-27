
import json
from pathlib import Path

from sentence_transformers import util


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BASE_DIR = PROJECT_ROOT / 'examples' / 'feature_extractor'

KEYWORDS_FILE = BASE_DIR / "result.json"
EXECUTORS_FILE = BASE_DIR / "executors.json"
OUTPUT_FILE = BASE_DIR / "matching_result.json"
MATCH_THRESHOLD = 0.40


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_matching(model, keywords, executor):
    skills = executor.get("skills", [])

    if not skills or not keywords:
        return {
            "executor_id": executor["id"],
            "executor_name": executor.get("name"),
            "score": 0.0,
            "matched_skills_count": 0,
            "matched_keywords": [],
        }

    phrases = [item["phrase"] for item in keywords]

    keyword_embeddings = model.encode(
        phrases,
        convert_to_tensor=True,
        normalize_embeddings=True,
    )

    skill_embeddings = model.encode(
        skills,
        convert_to_tensor=True,
        normalize_embeddings=True,
    )

    similarities = util.cos_sim(
        keyword_embeddings,
        skill_embeddings,
    )

    matched_keywords = []
    weighted_sum = 0.0
    total_weight = 0.0
    matched_skills = set()

    for i, keyword in enumerate(keywords):
        row = similarities[i]

        best_index = int(row.argmax().item())
        best_similarity = float(row[best_index].item())

        weight = max(float(keyword.get("weight", 1.0)), 0.0)

        if best_similarity >= MATCH_THRESHOLD:
            matched_skills.add(skills[best_index])

        weighted_sum += best_similarity * weight
        total_weight += weight

        matched_keywords.append({
            "keyword": keyword["phrase"],
            "matched_skill": skills[best_index],
            "similarity": round(best_similarity, 4),
            "weight": round(weight, 4),
        })

    score = (
        weighted_sum / total_weight
        if total_weight > 0
        else 0.0
    )

    return {
        "executor_id": executor["id"],
        "executor_name": executor.get("name"),
        "score": round(score, 4),
        "matched_skills_count": len(matched_skills),
        "matched_keywords": matched_keywords,
    }


def run_matching(model):
    """
    Рассчитывает соответствие исполнителей,
    используя уже загруженную модель.
    """

    keyword_data = load_json(KEYWORDS_FILE)
    executor_data = load_json(EXECUTORS_FILE)

    keywords = keyword_data.get("keywords", [])
    executors = executor_data.get("executors", [])

    results = []

    for executor in executors:
        result = calculate_matching(
            model=model,
            keywords=keywords,
            executor=executor,
        )
        results.append(result)

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    output = {
        "executors_count": len(results),
        "results": results,
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Исполнителей обработано: {len(results)}")

    for result in results:
        print(
            f'{result["executor_name"]}: '
            f'{result["score"]:.4f}'
        )

    print(f"Результат сохранён: {OUTPUT_FILE}")

    return output
