# Архитектура Executor Balancer

## 1. Назначение сервиса

Go-сервис принимает готовый ранжированный список исполнителей от Decision Engine, обеспечивает целостность, атомарно резервирует одного из кандидатов, сохраняет историю и отправляет назначение обратно в AIS Simulator.

Основной сценарий:

```text
AIS Simulator → Requests Kafka → Decision Engine
                                  ↓
                    Rule Engine / Feature Extractor
                                  ↓
                         ML Ranker / Balancer
                                  ↓
                       Decision.Result Kafka
                                  ↓
                             Go-сервис
                                  ↓
              проверка целостности и Redis Reservation
                                  ↓
                  PostgreSQL Assignment + Decision Trace
                                  ↓ HTTP
                            AIS Simulator
```

Rule Engine, Feature Extractor, ML Ranker и Balancer находятся внутри Python Decision Engine. Go-сервис не повторяет их расчёты и использует порядок `balanced_candidates`, полученный из `ExecutorDecisionCompleted`.

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
│   │   ├── decision/
│   │   │   ├── result.go
│   │   │   └── result_test.go
│   │   ├── decisiontrace/
│   │   │   └── model.go
│   │   └── event/
│   │       └── model.go
│   │
│   ├── services/
│   │   ├── system/
│   │   │   ├── service.go
│   │   │   └── service_test.go
│   │   ├── decision/
│   │   │   ├── service.go
│   │   │   └── service_test.go
│   │   ├── order/
│   │   ├── executor/
│   │   ├── rule/
│   │   ├── assignment/
│   │   ├── reservation/
│   │   └── dashboard/
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
│   │   │       ├── decisionresult/
│   │   │       │   ├── queries.go
│   │   │       │   ├── repository.go
│   │   │       │   └── repository_test.go
│   │   │       └── event/
│   │   │           ├── queries.go
│   │   │           ├── repository.go
│   │   │           └── repository_test.go
│   │   └── redis/
│   │       ├── client.go
│   │       ├── executors/
│   │       │   └── repository.go
│   │       └── reservations/
│   │           ├── repository.go
│   │           └── repository_test.go
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
│   │       └── handlers/
│   │           └── decision/
│   │               ├── handler.go
│   │               └── handler_test.go
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

Сервисный слой между `transport` и `repository`. `services/decision` проверяет результат Decision Engine, последовательно пробует кандидатов по `rank`, резервирует первого доступного и атомарно сохраняет Assignment вместе с Decision Trace.

### `internal/repository`

Интерфейсы доступа к данным и их реализация для PostgreSQL. Каждый PostgreSQL-репозиторий находится в отдельной папке: `queries.go` содержит SQL, `repository.go` — Go-код доступа к данным, `repository_test.go` — тесты. При необходимости рядом можно добавить `dto.go`. Остальные части приложения не выполняют SQL запросы напрямую.

### `internal/repository/redis`

Redis содержит только активных исполнителей и runtime-состояние. Репозиторий `reservations` атомарно создаёт, подтверждает, отменяет и очищает истёкшие резервации, изменяя `pending_count`, `active_count` и `current_load`.

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
KAFKA_DECISION_RESULT_TOPIC=decision.result.v1
AIS_BASE_URL=http://ais-simulator:8091
AIS_REQUEST_TIMEOUT=12s
RESERVATION_TTL=30s
```

Пароли приведены только для локального окружения хакатона и не должны использоваться в production.

## 5. Kafka topics

Для MVP используются следующие topic:

| Topic | Ключ сообщения | События |
|---|---|---|
| `ais.orders.v1` | `order_id` | `OrderCreated`, `OrderUpdated`, `OrderStatusChanged` |
| `ais.executors.v1` | `executor_id` | `ExecutorCreated`, `ExecutorUpdated` |
| `decision.result.v1` | `order_id` | `ExecutorDecisionCompleted` |

Дополнительный topic для сообщений, которые не удалось обработать:

```text
executor-balancer.dead-letter.v1
```

Правила обработки:

- сообщения одной заявки отправляются с одинаковым ключом `order_id`;
- сообщения одного исполнителя отправляются с одинаковым ключом `executor_id`;
- Kafka offset подтверждается только после успешного сохранения события;
- повторное событие определяется по `event_id`;
- повторный `ExecutorDecisionCompleted`, в котором заявка уже имеет pending или confirmed Assignment, не создаёт второе назначение;
- consumer group Executor Balancer: `executor-balancer-v1`;
- для локального демо допустимо `auto.offset.reset=earliest`;
- автоматическое подтверждение offset необходимо отключить.

## 6. Общий формат Kafka события AIS

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

Формат применяется к событиям AIS. `ExecutorDecisionCompleted` имеет отдельный плоский контракт из раздела 12. Неизвестный `event_type` или неподдерживаемая версия не должны приводить к падению consumer. Такое сообщение записывается как ошибка и отправляется в dead-letter topic.

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

## 9. Состояние исполнителей

PostgreSQL хранит всех исполнителей, Redis — только активных и их текущее runtime-состояние. При запуске выполняется полная синхронизация активных исполнителей, затем изменения активности и параметров приходят через Kafka `Executor, Requests parameters`.

В Redis для активного исполнителя хранятся:

```text
capacity
current_load
active_count
pending_count
processed_today
last_assignment_at
```

При деактивации исполнитель удаляется из Redis, но остаётся в PostgreSQL. Обновление со старой или равной `version` не должно откатывать состояние в PostgreSQL.

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
| `capacity` | number больше 0 | да | условная пропускная способность |
| `current_load` | number не меньше 0 | да | суммарный вес активных и pending заявок |
| `active_count` | integer не меньше 0 | да | количество активных заявок |
| `pending_count` | integer не меньше 0 | да | количество временно зарезервированных заявок |
| `processed_today` | integer не меньше 0 | да | количество обработанных сегодня заявок |
| `last_assignment_at` | datetime или null | да | время последнего назначения |
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

## 12. Результат Decision Engine

Rule Engine, Feature Extractor, ML Ranker и Balancer выполняются в Decision Engine. Go-сервис получает из Kafka готовый список:

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

Go проверяет тип и версию события, непустой строковый `order_id`, непрерывные ранги от 1, уникальность `executor_id`, конечность числовых значений и неотрицательность нагрузки и счётчиков. Затем кандидаты поочерёдно резервируются в Redis. Если `rank=1` уже занят конкурентным процессом или `current_load + order_weight` превышает его актуальный `capacity`, проверяется `rank=2`.

## 13. Формула нагрузки

```text
order_weight = complexity

base_capacity = median(completed_order_weight за последние 30 дней)
capacity = base_capacity × schedule_availability

для нового исполнителя base_capacity = 1.0

current_load = active_weight + pending_weight
effective_load = current_load / capacity
```

Расчёт и сортировка выполняются Decision Engine. Go хранит `capacity` и runtime-нагрузку в Redis и атомарно обновляет их при reservation, подтверждении, отмене и завершении заявки.

## 14. Владение данными

AIS Simulator является источником истины для:

- исходных заявок;
- бизнес-статуса заявки;
- исполнителей;
- настроек исполнителей.

Executor Balancer является источником истины для:

- истории расчётов;
- reservation;
- pending и active runtime-нагрузки;
- локальных назначений;
- Decision Trace;
- технических метрик.

Decision Engine отвечает за Rule Engine, Feature Extractor, ML Ranker, Balancer, расчёт `capacity`, `effective_load` и итоговый порядок кандидатов.

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
