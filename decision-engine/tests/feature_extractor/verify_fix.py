"""Full pipeline test: preprocess -> keywords -> skill matching on medical text."""
import json
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer
from keybert import KeyBERT

from decision_engine.feature_extractor.matching.preprocess import clean_text, split_into_sections
from decision_engine.feature_extractor.matching.keyword_filter import merge_keywords, is_valid_keyword
from decision_engine.feature_extractor.matching.skill_matching import calculate_matching

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / 'examples' / 'feature_extractor'
MODEL_PATH = PROJECT_ROOT / 'models' / 'feature-extractor' / 'matching' / 'models' / 'paraphrase-multilingual-MiniLM-L12-v2'

# 1. Read and preprocess
raw = (BASE_DIR / 'request.txt').read_text('utf-8')
processed = clean_text(raw)
print(f'Preprocessed: {len(processed)} chars')

# 2. Load model
model = SentenceTransformer(str(MODEL_PATH))

# 3. Extract keywords
kw_model = KeyBERT(model=model)
sections = split_into_sections(processed)
section_results = []
for section in sections:
    kws = kw_model.extract_keywords(
        section['text'],
        keyphrase_ngram_range=(1, 3),
        stop_words=None,
        top_n=10,
        use_mmr=True,
        diversity=0.5,
    )
    filtered = [{'phrase': p, 'weight': round(float(s), 4)} for p, s in kws if is_valid_keyword(p)]
    section_results.append({'section_title': section['title'], 'keywords': filtered})

keywords = merge_keywords(section_results)
print(f'\nExtracted {len(keywords)} keywords:')
for kw in keywords:
    print(f'  {kw["phrase"]:40} weight={kw["weight"]}')

# 4. Skill matching
executors = json.loads((BASE_DIR / 'executors.json').read_text('utf-8'))['executors']
print(f'\nExecutors: {[e["name"] for e in executors]}')
print(f'Skills:')
for e in executors:
    print(f'  {e["name"]}: {e["skills"]}')

print('\n=== MATCHING RESULTS ===')
results = []
for executor in executors:
    res = calculate_matching(model, keywords, executor)
    results.append(res)

results.sort(key=lambda r: r['score'], reverse=True)

for res in results:
    name = res['executor_name']
    score = res['score']
    msc = res['matched_skills_count']
    print(f'\n  {name}: score={score}  matched_skills_count={msc}')
    for mk in res['matched_keywords']:
        flag = ' ✓' if mk['similarity'] >= 0.40 else ''
        print(f'    {mk["keyword"]:40} -> {mk["matched_skill"]:18} sim={mk["similarity"]}{flag}')

# Save result
output = {'executors_count': len(results), 'results': results}
out_path = BASE_DIR / 'matching_result.json'
out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), 'utf-8')
print(f'\nResult saved to {out_path}')
