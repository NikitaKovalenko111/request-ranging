# Executor Rule Engine

Сервис читает заявку из Kafka, получает снимки онлайн-исполнителей из Redis,
применяет жёсткие бизнес-правила и публикует результат фильтрации обратно в
Kafka. Ранжирование и окончательное назначение исполнителя в этот сервис не
входят.

## Поток данных

```text
orders.created -> Kafka consumer -> Redis online executors
                                      |
                                      v
                                  RuleEngine
                                      |
                                      v
                         orders.rule-engine.completed
```

Offset входного сообщения подтверждается только после успешной публикации
результата. Невалидный JSON/контракт отправляется в DLQ. Инфраструктурная ошибка
не подтверждается, поэтому событие можно обработать повторно.

## Контракт Redis

Реализация не требует RedisJSON:

- `executors:online` — Redis Set с `user_id` онлайн-исполнителей;
- `executor:{user_id}` — строка с JSON-снимком исполнителя.
- `rules:active` — JSON-массив динамических правил или объект `{"rules": [...]}`.

Пример заполнения:

```redis
SADD executors:online 101
SET executor:101 '{"user_id":101,"active":true,"daily_count":3,"settings":{"min_accept_sum":1000,"max_accept_sum":500000,"min_reject_sum":null,"max_reject_sum":null,"client_msp":"MSP-1","executor_msp":"MSP-2","order_type":"ORDER_TYPE_1","subject":"96bc9564-fb0b-4db5-b4b6-ce11c2fb5e6f","vip":true,"max_daily_limit":20}}'
```

Поддерживается также плоский JSON, где поля `settings` находятся на верхнем
уровне. Отсутствующий `max_daily_limit` означает отсутствие лимита, а `0` — что
исполнитель сегодня не может получить ни одной заявки.

## Входное событие Kafka

Можно передать envelope:

```json
{
  "event_id": "8df09e75-4438-4f9e-bde9-bc890b2b22bd",
  "event_type": "OrderCreated",
  "order": {
    "id": 42,
    "parent_id": null,
    "user_id": 9001,
    "sum": 250000,
    "client_msp": "MSP-1",
    "executor_msp": "MSP-2",
    "order_type": "ORDER_1",
    "subject": "96bc9564-fb0b-4db5-b4b6-ce11c2fb5e6f",
    "vip": true,
    "text": "Текст заявки",
    "status": "processed"
  }
}
```

Поддерживается и заявка без envelope. Для неё `event_id` формируется из
Kafka topic/partition/offset.

## Начальные правила

- заявка имеет статус `processed`;
- исполнитель активен;
- суточный лимит не достигнут;
- сумма входит в accept-диапазон и не входит в reject-диапазон (границы
  включительно);
- совпадают `client_msp`, `executor_msp`, `order_type` и `subject`, если
  соответствующая настройка задана;
- VIP-заявка допускается только VIP-исполнителю. VIP-настройка трактуется как
  допуск, поэтому VIP-исполнитель может обработать обычную заявку.

`ORDER_TYPE_N` из настроек нормализуется в `ORDER_N` из заявки.

## Запуск

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
executor-rule-engine
```

Переменные из `.env` нужно загрузить средством окружения/оркестратора: сервис
намеренно не имеет скрытой зависимости от dotenv.

Тесты:

```powershell
pytest
```

## Динамические правила

Системными остаются только проверка статуса заявки, активности исполнителя и
суточного лимита. Остальные ограничения задаются JSON без изменения Python-кода.
Полный начальный набор находится в [`examples/rules.json`](examples/rules.json).

Backend, отвечающий за CRUD правил и PostgreSQL, должен записывать актуальный
набор в Redis-строку `rules:active`. Допустимы JSON-массив и объект
`{"rules": [...]}`. Rule Engine держит локальную копию пять секунд, после чего
перечитывает Redis. Интервал и ключ настраиваются через
`RULES_LOCAL_TTL_SECONDS` и `REDIS_RULES_KEY`.

Поддерживаются `AND`/`OR`, вложенные группы, приоритет, отключение и версия
правила, а также операторы `EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`,
`NOT_IN`, `BETWEEN`, `CONTAINS`, `NOT_CONTAINS`, `IS_NULL`, `IS_NOT_NULL`.

Доступные поля и операторы определены в `field_registry.py`. Метод
`DEFAULT_FIELD_REGISTRY.public_dict()` возвращает готовый контракт для будущего
backend endpoint `GET /rule-fields`; сам HTTP endpoint не входит в этот сервис.

Результат Kafka содержит `traces` для всех кандидатов. Для каждой проверки
указаны `rule_id`, `rule_version`, `condition`, значения операндов, оператор и
результат. Ошибка конфигурации rules-cache обрабатывается fail-closed: offset
заявки не подтверждается.

Пример загрузки начального набора через `redis-cli`:

```powershell
Get-Content -Raw examples/rules.json | redis-cli -x SET rules:active
```

Правило повторного назначения `parent_id` здесь пока не реализовано: для него
нужен отдельный контракт хранения предыдущего назначения, которого нет в
исходных таблицах.
