# Контракт Decision.Result

Go-сервис получает результат Decision Engine из Kafka topic `decision.result.v1`.

```json
{
  "event_type": "ExecutorDecisionCompleted",
  "event_version": 1,
  "occurred_at": "2026-09-27T10:00:00+00:00",
  "order_id": "order-1032",
  "balanced_candidates": [
    {
      "executor_id": "7",
      "rank": 1,
      "ml_score": 0.82,
      "effective_load": 0.2,
      "capacity": 1.0,
      "active_count": 1,
      "pending_count": 0,
      "processed_today": 5,
      "last_assignment_at": "2026-09-27T09:59:00+00:00"
    }
  ]
}
```

## Проверки целостности

- `event_type` равен `ExecutorDecisionCompleted`;
- `event_version` равен `1`;
- `order_id` — непустая строка; Decision Engine возвращает исходный идентификатор AIS без преобразования;
- `balanced_candidates` не пуст;
- каждый `executor_id` встречается один раз;
- кандидаты передаются в порядке `rank`: `1`, `2`, `3` и далее без пропусков;
- `ml_score`, `effective_load` и `capacity` — конечные числа;
- `capacity` больше нуля;
- нагрузка и счётчики неотрицательны;
- дополнительные JSON-поля не допускаются.

`last_assignment_at` может быть `null` для нового исполнителя.

## Обработка

Go-сервис последовательно пробует кандидатов по `rank`. Каждая попытка резервации выполняется атомарно в Redis. Если исполнитель уже зарезервирован другим параллельным процессом, сервис переходит к следующему кандидату.

После успешной резервации Assignment и Decision Trace сохраняются одной транзакцией PostgreSQL. При ошибке транзакции резервация компенсирующе отменяется.
