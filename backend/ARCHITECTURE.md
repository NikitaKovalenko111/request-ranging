# Архитектура Executor Balancer

## 1. Назначение сервиса

Executor Balancer принимает из сервиса симуляции сведения о заявках и исполнителях, определяет подходящего исполнителя, безопасно фиксирует назначение и отправляет результат обратно в сервис симуляции.

Основной сценарий:

```text
AIS Simulator
    ↓ Kafka
Executor Balancer
    ↓
Проверка повторной обработки
    ↓
Сохранение заявки и получение исполнителей
    ↓
Parent Handler
    ↓
Rule Engine
    ↓
Balancer
    ↓
Redis Reservation
    ↓
Создание Assignment
    ↓ HTTP
AIS Simulator
    ↓
Подтверждение или ошибка
    ↓
PostgreSQL и Decision Trace
```

Executor Balancer реализуется как одно Go приложение. Rule Engine, Balancer, Reservation и обработчики событий являются внутренними частями приложения, а не отдельными микросервисами.

## 2. Структура проекта

```text
backend/
├── cmd/
│   └── balancer/
│       └── main.go
│
├── internal/
│   ├── config/
│   │   ├── config.go
│   │   ├── app.go
│   │   ├── http.go
│   │   ├── postgres.go
│   │   ├── redis.go
│   │   ├── kafka.go
│   │   ├── ais.go
│   │   └── reservation.go
│   │
│   ├── models/
│   │   ├── order/
│   │   │   ├── model.go
│   │   │   └── model_test.go
│   │   ├── executor/
│   │   │   └── model.go
│   │   ├── rule/
│   │   │   ├── model.go
│   │   │   └── model_test.go
│   │   ├── assignment/
│   │   │   └── model.go
│   │   ├── reservation/
│   │   │   └── model.go
│   │   ├── decisiontrace/
│   │   │   └── model.go
│   │   └── event/
│   │       └── model.go
│   │
│   ├── services/
│   │   ├── system/
│   │   │   ├── service.go
│   │   │   └── service_test.go
│   │   ├── distribution/
│   │   │   ├── service.go
│   │   │   └── service_test.go
│   │   ├── order/
│   │   ├── executor/
│   │   ├── rule/
│   │   ├── assignment/
│   │   ├── reservation/
│   │   └── dashboard/
│   │
│   ├── distribution/
│   │   ├── parent_handler.go
│   │   ├── rule_engine.go
│   │   ├── operators.go
│   │   ├── balancer.go
│   │   ├── load_calculator.go
│   │   └── trace_builder.go
│   │
│   ├── repository/
│   │   ├── interfaces.go
│   │   ├── postgres/
│   │   │   ├── client.go
│   │   │   └── repositories/
│   │   │       ├── repositories.go
│   │   │       ├── shared/
│   │   │       │   └── helpers.go
│   │   │       ├── order/
│   │   │       │   ├── queries.go
│   │   │       │   ├── repository.go
│   │   │       │   └── repository_test.go
│   │   │       ├── executor/
│   │   │       │   ├── queries.go
│   │   │       │   ├── repository.go
│   │   │       │   └── repository_test.go
│   │   │       ├── rule/
│   │   │       │   ├── queries.go
│   │   │       │   ├── repository.go
│   │   │       │   └── repository_test.go
│   │   │       ├── assignment/
│   │   │       │   ├── queries.go
│   │   │       │   ├── repository.go
│   │   │       │   └── repository_test.go
│   │   │       ├── decisiontrace/
│   │   │       │   ├── queries.go
│   │   │       │   ├── repository.go
│   │   │       │   └── repository_test.go
│   │   │       └── event/
│   │   │           ├── queries.go
│   │   │           ├── repository.go
│   │   │           └── repository_test.go
│   │   └── redis/
│   │       ├── client.go
│   │       └── scripts.go
│   │
│   ├── transport/
│   │   ├── http/
│   │   │   ├── server.go
│   │   │   └── handlers/
│   │   │       ├── system/
│   │   │       │   ├── handler.go
│   │   │       │   ├── routes.go
│   │   │       │   └── handler_test.go
│   │   │       ├── order/
│   │   │       ├── executor/
│   │   │       ├── rule/
│   │   │       ├── assignment/
│   │   │       └── dashboard/
│   │   └── kafka/
│   │       ├── client.go
│   │       ├── consumer.go
│   │       ├── events.go
│   │       └── handlers.go
│   │
│   ├── integration/
│   │   └── ais/
│   │       ├── client.go
│   │       └── models.go
│   │
│   └── package/
│       ├── logger/
│       │   └── logger.go
│       └── metrics/
│           └── metrics.go
│
├── migrations/
│   ├── 001_initial.up.sql
│   └── 001_initial.down.sql
│
├── api/
│   ├── openapi.yaml
│   └── events.md
│
├── tests/
│   ├── integration/
│   └── load/
│
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── go.mod
├── Makefile
└── README.md
```

## 3. Ответственность каталогов

### `internal/models`

Основные структуры данных сервиса: заявка, исполнитель, правило, назначение, резервирование и история принятия решения. Каждая предметная область находится в собственной папке; рядом с моделью размещаются её тесты. Код в этом каталоге не должен обращаться к HTTP, Kafka, PostgreSQL или Redis.

### `internal/services`

Сервисный слой между `transport` и `repository`. Сервисы проверяют бизнес-условия, управляют сценариями и вызывают интерфейсы репозиториев. Сложный сценарий распределения находится в `services/distribution` и последовательно вызывает получение данных, правила, балансировку, резервирование и отправку назначения.

### `internal/distribution`

Вычислительная логика:

- проверка обязательных и динамических правил;
- расчёт нагрузки;
- сортировка кандидатов;
- обработка повторной заявки;
- построение объяснения решения.

### `internal/repository`

Интерфейсы доступа к данным и их реализация для PostgreSQL. Каждый PostgreSQL-репозиторий находится в отдельной папке: `queries.go` содержит SQL, `repository.go` — Go-код доступа к данным, `repository_test.go` — тесты. При необходимости рядом можно добавить `dto.go`. Остальные части приложения не выполняют SQL запросы напрямую.

### `internal/reservation`

Атомарное резервирование исполнителя в Redis, подтверждение, отмена и истечение временного резервирования.

### `internal/transport`

Входные точки приложения: HTTP API и Kafka consumer. Обработчики проверяют входные данные и вызывают сервисы из `internal/services`, но не содержат бизнес-логику распределения.

`server.go` создаёт HTTP router и хранит структуру обработчиков. Для каждой группы HTTP-методов создаётся отдельная папка в `transport/http/handlers`: `handler.go` содержит обработчик, `routes.go` регистрирует маршруты функцией вида `StartSystemHandler`, а `handler_test.go` содержит тесты.

### `internal/package`

Общие технические пакеты, не относящиеся к одной бизнес-функции, например логирование и метрики.

### `internal/integration/ais`

HTTP клиент для отправки назначения в AIS Simulator.

## 4. Параметры локального окружения

Для первой версии принимаются следующие значения:

| Компонент | Адрес внутри Docker Compose | Адрес с компьютера |
|---|---|---|
| Executor Balancer HTTP | `executor-balancer:8090` | `localhost:8090` |
| AIS Simulator HTTP | `ais-simulator:8091` | `localhost:8091` |
| PostgreSQL | `postgres:5432` | `localhost:5442` |
| Redis | `redis:6379` | `localhost:6379` |
| Kafka | `kafka:9092` | `localhost:9092` |

Параметры Executor Balancer:

```text
APP_HTTP_ADDR=:8090
POSTGRES_DSN=postgres://executor_balancer:executor_balancer@postgres:5432/executor_balancer?sslmode=disable
REDIS_ADDR=redis:6379
KAFKA_BROKERS=kafka:9092
KAFKA_CONSUMER_GROUP=executor-balancer-v1
AIS_BASE_URL=http://ais-simulator:8091
AIS_REQUEST_TIMEOUT=12s
RESERVATION_TTL=30s
```

Пароли приведены только для локального окружения хакатона и не должны использоваться в production.

## 5. Kafka topics

Для MVP используются два входящих topic:

| Topic | Ключ сообщения | События |
|---|---|---|
| `ais.orders.v1` | `order_id` | `OrderCreated`, `OrderUpdated`, `OrderStatusChanged` |
| `ais.executors.v1` | `executor_id` | `ExecutorCreated`, `ExecutorUpdated` |

Дополнительный topic для сообщений, которые не удалось обработать:

```text
executor-balancer.dead-letter.v1
```

Правила обработки:

- сообщения одной заявки отправляются с одинаковым ключом `order_id`;
- сообщения одного исполнителя отправляются с одинаковым ключом `executor_id`;
- Kafka offset подтверждается только после успешного сохранения события;
- повторное событие определяется по `event_id`;
- consumer group Executor Balancer: `executor-balancer-v1`;
- для локального демо допустимо `auto.offset.reset=earliest`;
- автоматическое подтверждение offset необходимо отключить.

## 6. Общий формат Kafka события

```json
{
  "event_id": "9ba08c58-4037-4480-a45a-f90a033ab7db",
  "event_type": "OrderCreated",
  "event_version": 1,
  "occurred_at": "2026-09-25T12:00:00Z",
  "source": "ais-simulator",
  "payload": {}
}
```

Требования:

- `event_id` — UUID, уникальный для каждого события;
- `event_type` — одно из согласованных названий;
- `event_version` — для MVP всегда `1`;
- `occurred_at` — UTC в формате RFC 3339;
- `source` — для событий симулятора `ais-simulator`;
- `payload` — данные конкретного события.

Неизвестный `event_type` или неподдерживаемая версия не должны приводить к падению consumer. Такое сообщение записывается как ошибка и отправляется в dead-letter topic.

## 7. События заявок

### `OrderCreated`

```json
{
  "event_id": "9ba08c58-4037-4480-a45a-f90a033ab7db",
  "event_type": "OrderCreated",
  "event_version": 1,
  "occurred_at": "2026-09-25T12:00:00Z",
  "source": "ais-simulator",
  "payload": {
    "order_id": "order-1032",
    "parent_id": null,
    "status": "processed",
    "weight": 2.0,
    "version": 1,
    "attributes": {
      "sum": 900000,
      "client_msp": "medium",
      "executor_msp": "legal",
      "order_type": "LEGAL_REVIEW",
      "subject": "contract",
      "vip": true,
      "text": "Срочная проверка договора",
      "region": "ural"
    }
  }
}
```

### `OrderUpdated`

Содержит полный актуальный снимок заявки в том же формате, что и `OrderCreated`. Поле `version` увеличивается при каждом изменении.

Executor Balancer не должен применять событие, если его `version` меньше или равна уже сохранённой версии заявки.

### `OrderStatusChanged`

```json
{
  "event_id": "39212981-6db7-44ec-ae15-df2c70ca1dd2",
  "event_type": "OrderStatusChanged",
  "event_version": 1,
  "occurred_at": "2026-09-25T12:10:00Z",
  "source": "ais-simulator",
  "payload": {
    "order_id": "order-1032",
    "previous_status": "processed",
    "status": "accept",
    "version": 2
  }
}
```

## 8. Статусы заявки

Бизнес-статусы заявки приходят из AIS Simulator:

| Статус | Значение |
|---|---|
| `processed` | заявка находится в работе или ожидает назначения |
| `await` | заявка возвращена на доработку |
| `accept` | заявка успешно завершена |
| `reject` | заявка завершена отказом |

Техническое состояние назначения хранится отдельно и не смешивается с бизнес-статусом заявки:

| Статус назначения | Значение |
|---|---|
| `pending` | назначение отправлено или ожидает подтверждения |
| `confirmed` | АИС подтвердила назначение |
| `cancelled` | временное назначение отменено |
| `failed` | назначение завершилось ошибкой |

## 9. События исполнителей

### `ExecutorCreated` и `ExecutorUpdated`

Оба события содержат полный актуальный снимок исполнителя:

```json
{
  "event_id": "3b7ea016-496c-440e-9137-3248c20561d9",
  "event_type": "ExecutorUpdated",
  "event_version": 1,
  "occurred_at": "2026-09-25T12:00:00Z",
  "source": "ais-simulator",
  "payload": {
    "executor_id": "executor-28",
    "active": true,
    "capacity": 1.5,
    "daily_limit": 100,
    "version": 3,
    "attributes": {
      "min_accept_sum": 0,
      "max_accept_sum": 1000000,
      "client_msp": ["small", "medium"],
      "executor_msp": ["legal"],
      "order_types": ["LEGAL_REVIEW", "CONSULTATION"],
      "subjects": ["contract", "claims"],
      "vip_allowed": true,
      "regions": ["ural", "siberia"]
    }
  }
}
```

Правила полей:

- `capacity` должна быть больше нуля;
- `daily_limit` может быть `null`, что означает отсутствие лимита;
- `version` увеличивается при каждом изменении;
- текущая нагрузка не передаётся симулятором как источник истины, её считает Executor Balancer;
- событие со старой или равной версией не должно откатывать данные исполнителя назад.

## 10. Поля заявки и исполнителя

Минимально согласованный набор параметров заявки:

| Поле | Тип | Обязательное | Назначение |
|---|---|---|---|
| `order_id` | string | да | уникальный идентификатор |
| `parent_id` | string или null | нет | связь с предыдущей заявкой |
| `status` | string | да | бизнес-статус |
| `weight` | number больше 0 | да | сложность заявки |
| `version` | integer больше 0 | да | версия данных |
| `attributes.sum` | integer | да | сумма заявки |
| `attributes.order_type` | string | да | тип заявки |
| `attributes.subject` | string | да | тематика |
| `attributes.vip` | boolean | да | VIP признак |
| `attributes.client_msp` | string | нет | категория клиента |
| `attributes.executor_msp` | string | нет | требуемая категория исполнителя |
| `attributes.text` | string | нет | описание заявки |
| `attributes.region` | string | нет | регион |

Минимально согласованный набор параметров исполнителя:

| Поле | Тип | Обязательное | Назначение |
|---|---|---|---|
| `executor_id` | string | да | уникальный идентификатор |
| `active` | boolean | да | доступность для распределения |
| `capacity` | number больше 0 | да | относительная производительность |
| `daily_limit` | integer или null | да | суточный лимит или отсутствие лимита |
| `version` | integer больше 0 | да | версия данных |
| `attributes.min_accept_sum` | integer | нет | минимальная сумма |
| `attributes.max_accept_sum` | integer | нет | максимальная сумма |
| `attributes.order_types` | array of string | нет | допустимые типы заявок |
| `attributes.subjects` | array of string | нет | допустимые тематики |
| `attributes.vip_allowed` | boolean | нет | возможность обработки VIP |
| `attributes.client_msp` | array of string | нет | допустимые категории клиентов |
| `attributes.executor_msp` | array of string | нет | категории исполнителя |
| `attributes.regions` | array of string | нет | допустимые регионы |

## 11. API назначения в AIS Simulator

### Запрос

```http
POST /api/v1/assignments
Content-Type: application/json
Idempotency-Key: 7a44af14-b17b-45e2-8cb9-f17690252e92
```

```json
{
  "assignment_id": "7a44af14-b17b-45e2-8cb9-f17690252e92",
  "order_id": "order-1032",
  "executor_id": "executor-28",
  "decided_at": "2026-09-25T12:00:01Z"
}
```

`Idempotency-Key` равен `assignment_id`.

### Успешный ответ

```http
200 OK
```

```json
{
  "assignment_id": "7a44af14-b17b-45e2-8cb9-f17690252e92",
  "order_id": "order-1032",
  "executor_id": "executor-28",
  "status": "confirmed",
  "confirmed_at": "2026-09-25T12:00:08Z"
}
```

AIS Simulator имитирует задержку ответа от 2 до 10 секунд.

### Ошибки

| HTTP код | Смысл | Действие Executor Balancer |
|---|---|---|
| `400` | повреждённый JSON | не повторять, отменить reservation |
| `404` | заявка или исполнитель не найдены | не повторять, отменить reservation |
| `409` | заявка уже назначена другому исполнителю | не повторять, синхронизировать состояние |
| `422` | исполнитель не может быть назначен | отменить reservation, попробовать следующего кандидата |
| `500` | внутренняя ошибка симулятора | повторить запрос |
| `503` | симулятор временно недоступен | повторить запрос |

Повторный запрос с тем же `assignment_id` должен возвращать тот же результат без создания второго назначения. Если заявка уже назначена тому же исполнителю с тем же `assignment_id`, AIS Simulator возвращает `200 OK`.

Параметры повторов:

```text
тайм-аут одного запроса: 12 секунд
максимум попыток: 3
задержки между повторами: 500 мс, 1 секунда, 2 секунды
```

На всех попытках используется один и тот же `assignment_id`.

## 12. Правила распределения первой версии

В MVP должны поддерживаться операции:

```text
=
!=
>
>=
<
<=
IN
NOT IN
BETWEEN
CONTAINS
```

Минимальный набор обязательных правил:

1. Участвуют только активные исполнители.
2. Суточный лимит не должен быть превышен.
3. Сумма заявки должна входить в допустимый диапазон исполнителя, если диапазон настроен.
4. Тип заявки должен входить в `order_types`, если список настроен.
5. Тематика должна входить в `subjects`, если список настроен.
6. VIP заявка может быть назначена только при `vip_allowed = true`.
7. Регион должен входить в `regions`, если список настроен.
8. Все активные правила являются обязательными: достаточно одного отказа, чтобы исключить исполнителя.

Для повторной заявки с `parent_id` предыдущему исполнителю не проверяется только суточный лимит. Активность и остальные правила продолжают действовать.

## 13. Формула нагрузки

```text
effective_load =
    (confirmed_weight + pending_weight)
    / capacity
```

Кандидаты сортируются по:

1. меньшей `effective_load`;
2. меньшему количеству открытых заявок;
3. более старому времени последнего назначения;
4. `executor_id` для стабильного результата.

Случайный выбор не используется.

## 14. Владение данными

AIS Simulator является источником истины для:

- исходных заявок;
- бизнес-статуса заявки;
- исполнителей;
- настроек исполнителей.

Executor Balancer является источником истины для:

- истории расчётов;
- правил распределения;
- reservation;
- pending и confirmed нагрузки;
- локальных назначений;
- Decision Trace;
- технических метрик.

Сервисы не должны напрямую читать или изменять базы данных друг друга.

## 15. Вопросы, которые нужно подтвердить с разработчиком AIS Simulator

До интеграции необходимо подтвердить:

1. Используются ли точные адреса и порты из этого документа.
2. Поддерживаются ли Kafka topics `ais.orders.v1` и `ais.executors.v1`.
3. Поддерживаются ли все названия событий и общий envelope.
4. Передаёт ли `OrderUpdated` полный снимок заявки.
5. Передаёт ли `ExecutorUpdated` полный снимок исполнителя.
6. Всегда ли увеличивается `version` при изменении.
7. Реализован ли `POST /api/v1/assignments`.
8. Поддерживается ли идемпотентность по `assignment_id`.
9. Какие сценарии вызывают ответы `409` и `422`.
10. Как симулятор создаёт новую заявку после статуса `await` и заполняет `parent_id`.

После подтверждения параметры необходимо перенести в `api/openapi.yaml`, `api/events.md` и `.env.example` без изменения смысла.
