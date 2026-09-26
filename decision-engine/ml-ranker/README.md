# ML Ranker v1

Локальный Learning-to-Rank модуль для ранжирования уже допустимых исполнителей.
Он не проверяет hard constraints, не учитывает текущую нагрузку/fairness и не
назначает исполнителя. Эти задачи остаются у Rule Engine и Balancer.

## Pipeline

```text
Synthetic orders + executors
            ↓
FeatureBuilder(Order, Executor)
            ↓
grouped dataset (group_id = order_id)
            ↓
temporal group split
            ↓
HeuristicRanker baseline ↔ CatBoostRanker
            ↓
NDCG@5 + MRR + HitRate@1
            ↓
ranker-v1.cbm + metadata.json
            ↓
local inference
```

Синтетические labels показывают работоспособность pipeline, но не являются
доказательством качества на реальных данных АИС. Production-модель потребует
исторических outcome-событий, вычисленных строго на момент создания заявки.

## Feature Contract v1

Контракт находится в `src/feature_builder.py`. Он включает:

- нормализованные агрегаты исполнителя;
- confidence на основе объёма истории;
- нормализованную историческую скорость;
- pair-признаки соответствия сложности опыту и срочности скорости;
- взаимодействия надёжности, сложности и исторической успешности.

В признаки намеренно не входят:

- активность и другие hard constraints;
- текущая/ожидающая нагрузка;
- fairness;
- ID заявки или исполнителя;
- скрытая формула synthetic generator;
- текст, LLM и skills.

## Установка

```powershell
cd decision-engine/ml-ranker
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Поддерживается Python 3.11+.

## Обучение

Полный локальный запуск генерирует dataset, делит его по целым группам заявок,
обучает CatBoost и сравнивает его с baseline:

```powershell
python -m src.train
```

Быстрый smoke-run:

```powershell
python -m src.train --orders 300 --candidates 8 --executors 100 --iterations 50
```

Артефакты:

- `data/processed/ranking_dataset.csv`;
- `models/ranker-v1.cbm`;
- `models/ranker-v1.metadata.json` с feature contract, параметрами выборки и
  метриками baseline/ML.

Значения по умолчанию находятся в `config.py`: 5 000 заявок × 10 кандидатов,
350 итераций CatBoost, `YetiRankPairwise`.

## Локальный inference

```powershell
python -m src.inference
```

Если обученная модель отсутствует, пример автоматически использует
`HeuristicRanker`. Это cold-start/fallback режим. CatBoost score преобразуется
сигмоидой в диапазон `[0, 1]`; он остаётся относительной оценкой, а не
калиброванной вероятностью успеха.

Программный интерфейс:

```python
ranker = MLRanker(model_path, metadata_path)
ranking = ranker.rank(order, eligible_executors)
```

На вход должны подаваться только кандидаты, прошедшие Rule Engine.

## Тесты

```powershell
pytest
```

Проверяются воспроизводимость генератора, целостность групп, отсутствие leakage
между split, Feature Contract, ranking-метрики и локальный heuristic inference.

## Не входит в v1

Kafka, Redis, REST API, Rule Engine, Balancer, LLM, online learning,
автоматическое переобучение и интеграция с АИС намеренно не реализованы.

