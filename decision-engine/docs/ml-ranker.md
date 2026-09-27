# ML Ranker v2

ML Ranker сортирует исполнителей, которые уже прошли Rule Engine. Он не
проверяет обязательные ограничения и не учитывает текущую нагрузку — это задача
Balancer.

## Подготовка обучающего датасета

```text
Synthetic order text + executor skills
                    ↓
          Feature Extractor
                    ↓
complexity, urgency, effort, keywords, skill match
                    ↓
             Feature Builder
                    ↓
 grouped ranking dataset (group_id = order_id)
                    ↓
       temporal train/validation/test split
                    ↓
              CatBoostRanker
```

Генератор сначала создаёт текст заявки и навыки исполнителей, а затем вызывает
тот же контракт Feature Extractor, который используется в runtime. Поэтому
датасет v2 больше не подставляет complexity и urgency напрямую.

Синтетические relevance-метки назначаются относительно кандидатов одной
заявки:

- лучший кандидат — 3;
- следующие 20% — 2;
- следующие 40% — 1;
- остальные — 0.

Это демонстрационный датасет. Для production модель необходимо переобучить на
исторических результатах обработки реальных заявок.

## Feature Contract v2

Контракт определён в
`src/decision_engine/ml_ranker/feature_builder.py`.

Признаки заявки из Feature Extractor:

- `order_complexity`;
- `order_urgency`;
- `order_estimated_effort`;
- `order_keyword_count`.

Признаки исполнителя:

- `experience_score`;
- `speed_score`;
- `reliability_score`;
- `historical_success_rate`;
- `skill_match_score`;
- нормализованная историческая скорость;
- confidence на основе количества исторических заявок.

Парные признаки заявки и исполнителя:

- соответствие сложности опыту;
- соответствие срочности скорости;
- соответствие трудозатрат опыту;
- взаимодействие skill matching и опыта;
- надёжность при заданной сложности;
- confidence исторической успешности.

В признаки намеренно не входят:

- hard constraints;
- текущая и ожидающая нагрузка;
- fairness;
- идентификаторы заявки и исполнителя.

## Артефакты v2

```text
data/processed/ranking_dataset_v2.csv
models/ranker-v2.cbm
models/ranker-v2.metadata.json
```

Полный датасет содержит:

- 5 000 заявок;
- 10 кандидатов на заявку;
- 50 000 строк;
- текст и диагностические результаты Feature Extractor;
- 19 числовых признаков модели.

## Обучение

Из корня `decision-engine`:

```powershell
.venv\Scripts\decision-ranker-train
```

Или:

```powershell
.venv\Scripts\python -m decision_engine.ml_ranker.train
```

Быстрый smoke-run:

```powershell
.venv\Scripts\python -m decision_engine.ml_ranker.train --orders 300 --candidates 8 --executors 100 --iterations 50
```

## Метрики текущей модели

На 500 тестовых заявках:

| Модель | NDCG@5 | MRR | HitRate@1 |
|---|---:|---:|---:|
| Heuristic baseline | 0.8603 | 0.7328 | 0.578 |
| CatBoostRanker v2 | 0.8756 | 0.7514 | 0.602 |

Метрики относятся только к синтетическому датасету и не являются оценкой
качества на реальных данных.

## Локальный inference

```powershell
.venv\Scripts\decision-ranker-demo
```

Если модель v2 отсутствует или её feature contract отличается от runtime,
используется `HeuristicRanker`.

## Тесты

```powershell
.venv\Scripts\python -m pytest tests\ml_ranker
```
