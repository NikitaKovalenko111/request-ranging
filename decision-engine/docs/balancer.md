# Python Balancer — Runtime Load

Balancer получает кандидатов после Rule Engine и ML Ranker, одним batch-запросом
читает их runtime-нагрузку из Redis и возвращает весь список в новом порядке.

Он не повторяет hard-фильтрацию и не выполняет reservation или assignment.

## Формула

```text
effective_load = (active_weight + pending_weight) / capacity
```

`pending_weight` учитывается полностью: назначение может подтверждаться во
внешней АИС 2–10 секунд и в этот период не должно выглядеть свободной capacity.

Кандидаты сортируются по следующим критериям:

1. меньший `effective_load`;
2. меньшее суммарное число `active_count + pending_count`;
3. больший `ml_score`;
4. меньший `processed_today`;
5. более давнее `last_assignment_at` (`None` — ещё не назначался);
6. `executor_id` для детерминированности.

Если `capacity <= 0`, effective load считается бесконечным. Кандидат остаётся в
результате, но не получает преимущество и сортируется после кандидатов с
корректной capacity.

## Redis-контракт

Read-only ключ:

```text
executor:load:{executor_id}
```

Значение — JSON:

```json
{
  "active_count": 7,
  "active_weight": 12.5,
  "pending_count": 2,
  "pending_weight": 4.0,
  "processed_today": 38,
  "last_assignment_at": "2026-09-27T10:30:00Z"
}
```

`RedisLoadRepository` использует один `MGET` на весь список. Отсутствующий ключ
превращается в `ExecutorLoad()` с нулевой нагрузкой. Ошибка Redis или повреждённый
JSON вызывает явный `LoadRepositoryError`; вся недоступная Redis не трактуется
как «все свободны».

## Использование

```python
from redis.asyncio import Redis
from decision_engine.balancer import (
    Balancer,
    BalancerCandidate,
    BalancerOrder,
    RedisLoadRepository,
)

redis = Redis.from_url("redis://localhost:6379/0", decode_responses=True)
balancer = Balancer(RedisLoadRepository(redis))

ranking = await balancer.balance(
    BalancerOrder(order_id="O-42", weight=2.0),
    [
        BalancerCandidate("executor-28", ml_score=0.87, capacity=1.5),
        BalancerCandidate("executor-14", ml_score=0.84, capacity=1.0),
    ],
)

payload = [candidate.as_dict() for candidate in ranking]
```

`BalancerCandidate.from_mapping()` понимает как `ml_score`, так и `score` из
текущего локального ML Ranker.

Минимальный результат:

```json
{
  "executor_id": "executor-28",
  "rank": 1,
  "ml_score": 0.87,
  "effective_load": 2.4
}
```

Реальная модель также возвращает capacity, счётчики и время последнего
назначения для Decision Trace.

Пустой список кандидатов возвращает `[]` без обращения к Redis.

## Структура

- `schemas.py` — входные и выходные модели;
- `load_repository.py` — изолированный read-only Redis adapter;
- `scoring.py` — чистые функции расчёта и сортировки;
- `balancer.py` — async orchestration одного batch-чтения.

## Установка и тесты

```powershell
cd decision-engine/balancer
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Не входит в модуль

- запись или обновление runtime state;
- Atomic Reservation;
- retry после reservation conflict;
- Go Backend, Kafka и AIS assignment;
- PostgreSQL persistence;
- Rule Engine, ML Ranker и Feature Extractor.

Справедливость при параллельной обработке зависит от своевременного атомарного
обновления pending load внешним runtime/orchestration слоем.

