# Контракт разработки AIS Simulator

## 1. Назначение документа

Этот документ описывает контракт между AIS Simulator и Executor Balancer. Он предназначен для разработчика AIS Simulator и фиксирует адреса, Kafka topics, форматы событий, HTTP API и ожидаемое поведение симулятора.

AIS Simulator разрабатывается независимо от Executor Balancer. Сервисы взаимодействуют только через Kafka и HTTP и не обращаются к базам данных друг друга.

## 2. Роль AIS Simulator

AIS Simulator эмулирует внешнюю информационную систему. Он должен:

- хранить заявки;
- хранить исполнителей и их настройки;
- предоставлять CRUD API;
- публиковать изменения заявок и исполнителей в Kafka;
- принимать назначение от Executor Balancer;
- имитировать задержку подтверждения от 2 до 10 секунд;
- изменять статусы заявок;
- создавать повторные заявки с `parent_id`;
- поддерживать генерацию нагрузки для демонстрации.

AIS Simulator является источником истины для исходных заявок, исполнителей, их настроек и бизнес-статусов заявок.

## 3. Адреса и порты

| Компонент | Локальный адрес |
|---|---|
| Executor Balancer | `http://localhost:8090` |
| AIS Simulator | `http://localhost:8091` |
| PostgreSQL | `localhost:5442` |
| Redis | `localhost:6379` |
| Kafka | `localhost:9092` |

AIS Simulator должен слушать порт `8091`.

Рекомендуемые переменные окружения:

```text
APP_HTTP_ADDR=:8091
KAFKA_BROKERS=kafka:9092
ORDER_TOPIC=ais.orders.v1
EXECUTOR_TOPIC=ais.executors.v1
ASSIGNMENT_DELAY_MIN=2s
ASSIGNMENT_DELAY_MAX=10s
```

Если AIS Simulator запускается вне Docker, Kafka доступна по `localhost:9092`.

## 4. Kafka topics

AIS Simulator публикует события в следующие topics:

| Topic | Ключ сообщения | События |
|---|---|---|
| `ais.orders.v1` | `order_id` | `OrderCreated`, `OrderUpdated`, `OrderStatusChanged` |
| `ais.executors.v1` | `executor_id` | `ExecutorCreated`, `ExecutorUpdated` |

Executor Balancer использует consumer group:

```text
executor-balancer-v1
```

Topic для сообщений, которые Executor Balancer не смог обработать:

```text
executor-balancer.dead-letter.v1
```

AIS Simulator не обязан читать dead-letter topic в MVP.

## 5. Общий формат события

Каждое Kafka событие имеет одинаковую внешнюю структуру:

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

Правила:

- `event_id` — новый UUID для каждого события;
- `event_type` — одно из согласованных названий;
- `event_version` — в первой версии всегда `1`;
- `occurred_at` — время UTC в формате RFC 3339;
- `source` — всегда `ais-simulator`;
- `payload` — полный набор данных конкретного события;
- одно и то же событие при повторной отправке сохраняет прежний `event_id`;
- разные события об одном объекте получают разные `event_id`.

Сообщения одной заявки публикуются с Kafka key, равным `order_id`. Сообщения одного исполнителя публикуются с key, равным `executor_id`.

## 6. Модель заявки

```json
{
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
```

Обязательные поля:

| Поле | Тип | Описание |
|---|---|---|
| `order_id` | string | уникальный идентификатор заявки |
| `parent_id` | string или null | идентификатор предыдущей заявки |
| `status` | string | бизнес-статус заявки |
| `weight` | number больше 0 | сложность заявки |
| `version` | integer больше 0 | версия данных заявки |
| `attributes.sum` | integer | сумма заявки |
| `attributes.order_type` | string | тип заявки |
| `attributes.subject` | string | тематика |
| `attributes.vip` | boolean | VIP признак |

Дополнительные поля:

- `attributes.client_msp`;
- `attributes.executor_msp`;
- `attributes.text`;
- `attributes.region`.

## 7. Статусы заявки

| Статус | Значение |
|---|---|
| `processed` | заявка находится в работе или ожидает назначения |
| `await` | заявка возвращена на доработку |
| `accept` | заявка успешно завершена |
| `reject` | заявка завершена отказом |

Рекомендуемые переходы:

```text
processed → accept
processed → reject
processed → await
await → новая заявка со статусом processed и заполненным parent_id
```

После `await` рекомендуется создавать новую заявку, а не переводить старую обратно в `processed`. У новой заявки:

- новый `order_id`;
- `parent_id` равен ID предыдущей заявки;
- `status` равен `processed`;
- параметры могут быть изменены пользователем;
- публикуется событие `OrderCreated`.

## 8. События заявок

### `OrderCreated`

Публикуется после успешного создания заявки.

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
      "order_type": "LEGAL_REVIEW",
      "subject": "contract",
      "vip": true,
      "region": "ural"
    }
  }
}
```

### `OrderUpdated`

Публикуется после изменения параметров заявки. Событие содержит полный актуальный снимок заявки, а не только изменившиеся поля.

При каждом изменении `version` увеличивается на единицу.

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

Событие публикуется только после успешного сохранения нового статуса в AIS Simulator.

## 9. Модель исполнителя

```json
{
  "executor_id": "executor-28",
  "active": true,
  "capacity": 1.5,
  "daily_limit": 100,
  "version": 3,
  "skills": [
    "Python",
    "PostgreSQL",
    "Docker"
  ],
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
```

Правила:

- `executor_id` уникален;
- `active` определяет участие в распределении;
- `capacity` должна быть больше нуля;
- `daily_limit` может быть `null`, что означает отсутствие лимита;
- `version` начинается с `1` и увеличивается при изменении;
- `skills` — список навыков исполнителя (массив строк на верхнем уровне модели);
- AIS Simulator не рассчитывает `pending_weight` и `confirmed_weight` — это ответственность Executor Balancer.

## 10. События исполнителей

### `ExecutorCreated`

Публикуется после успешного создания исполнителя и содержит полный снимок исполнителя.

### `ExecutorUpdated`

Публикуется после изменения активности, capacity, лимита или attributes. Также содержит полный актуальный снимок исполнителя.

Пример:

```json
{
  "event_id": "3b7ea016-496c-440e-9137-3248c20561d9",
  "event_type": "ExecutorUpdated",
  "event_version": 1,
  "occurred_at": "2026-09-25T12:00:00Z",
  "source": "ais-simulator",
  "payload": {
    "executor_id": "executor-28",
    "active": false,
    "capacity": 1.5,
    "daily_limit": 100,
    "version": 4,
    "skills": [
      "Python",
      "PostgreSQL",
      "Docker"
    ],
    "attributes": {
      "min_accept_sum": 0,
      "max_accept_sum": 1000000,
      "order_types": ["LEGAL_REVIEW"],
      "subjects": ["contract"],
      "vip_allowed": true,
      "regions": ["ural"]
    }
  }
}
```

## 11. Минимальное HTTP API AIS Simulator

### Заявки

```text
POST  /api/v1/orders
GET   /api/v1/orders
GET   /api/v1/orders/{id}
PATCH /api/v1/orders/{id}
```

`POST /orders` создаёт заявку и публикует `OrderCreated`.

`PATCH /orders/{id}`:

- при изменении параметров публикует `OrderUpdated`;
- при изменении статуса публикует `OrderStatusChanged`;
- при одновременном изменении параметров и статуса может опубликовать оба события с последовательными версиями.

### Исполнители

```text
POST  /api/v1/executors
GET   /api/v1/executors
GET   /api/v1/executors/{id}
PATCH /api/v1/executors/{id}
```

`POST /executors` публикует `ExecutorCreated`.

`PATCH /executors/{id}` публикует `ExecutorUpdated`.

### Назначения

```text
POST /api/v1/assignments
```

Этот endpoint вызывается Executor Balancer.

## 12. Контракт назначения

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

`Idempotency-Key` должен совпадать с `assignment_id`.

Перед ответом AIS Simulator ждёт случайное время от 2 до 10 секунд.

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

После успешного назначения AIS Simulator сохраняет связь заявки с исполнителем.

### Идемпотентность

Повторный запрос с тем же `assignment_id`:

- не создаёт второе назначение;
- не повторяет изменение заявки;
- возвращает тот же успешный результат;
- может вернуть ответ без повторной задержки.

Если заявка уже назначена другому исполнителю другим `assignment_id`, возвращается `409 Conflict`.

### Ошибки

| HTTP код | Причина |
|---|---|
| `400` | неправильный JSON или отсутствует обязательное поле |
| `404` | заявка или исполнитель не найдены |
| `409` | заявка уже назначена другому исполнителю |
| `422` | исполнитель неактивен или назначение запрещено состоянием заявки |
| `500` | внутренняя ошибка |
| `503` | временная недоступность, используемая в сценариях тестирования |

Формат ошибки:

```json
{
  "code": "ORDER_ALREADY_ASSIGNED",
  "message": "Order order-1032 is already assigned",
  "retryable": false
}
```

## 13. Генератор заявок

Для демонстрации AIS Simulator должен уметь создавать заявки с настраиваемой скоростью.

Минимальные режимы:

```text
1 заявка в секунду
10 заявок в секунду
BURST 100 заявок
```

При генерации варьируются:

- вес;
- сумма;
- тип;
- тематика;
- VIP;
- регион;
- текст заявки;
- наличие `parent_id` для отдельных сценариев.

Можно реализовать CLI, отдельный скрипт или внутренний HTTP endpoint. Конкретная форма запуска не является частью межсервисного контракта.

## 14. Симуляция работы исполнителей

Симулятор должен уметь:

- завершить заявку со статусом `accept`;
- завершить заявку со статусом `reject`;
- перевести заявку в `await`;
- после `await` создать новую заявку с `parent_id`;
- случайно активировать и деактивировать исполнителей;
- изменять настройки исполнителей;
- публиковать соответствующие Kafka события.

## 15. Рекомендуемые тестовые данные

Для демонстрации рекомендуется создать не менее 20 исполнителей:

- разные `capacity`: `0.5`, `1.0`, `1.5`, `2.0`;
- разные суточные лимиты;
- часть без лимита;
- несколько неактивных;
- разные типы заявок и тематики;
- часть с поддержкой VIP;
- разные регионы.

Заявки должны включать как минимум три типа:

```text
LEGAL_REVIEW
CONSULTATION
CLAIM_PROCESSING
```

Рекомендуемые тематики:

```text
contract
claims
payments
compliance
```

## 16. Что AIS Simulator не должен делать

AIS Simulator не должен:

- самостоятельно выбирать исполнителя;
- рассчитывать fairness;
- рассчитывать pending или confirmed нагрузку;
- выполнять правила распределения;
- обращаться к Redis Executor Balancer;
- обращаться к PostgreSQL Executor Balancer;
- изменять таблицы Executor Balancer напрямую.

## 17. Критерии готовности

AIS Simulator считается готовым к интеграции, когда:

- запускается на `localhost:8091`;
- подключается к Kafka `localhost:9092`;
- предоставляет CRUD заявок и исполнителей;
- публикует все согласованные события;
- использует правильные Kafka keys;
- увеличивает `version` при изменениях;
- принимает `POST /api/v1/assignments`;
- задерживает подтверждение на 2–10 секунд;
- повторный `assignment_id` не создаёт дубликат;
- поддерживает `409` и `422`;
- умеет создавать повторную заявку с `parent_id`;
- может создать поток заявок для демонстрации;
- не зависит от внутренней реализации Executor Balancer.

## 18. Интеграционная проверка

Минимальный совместный сценарий:

1. В AIS Simulator создаётся активный исполнитель.
2. В `ais.executors.v1` публикуется `ExecutorCreated`.
3. В AIS Simulator создаётся заявка.
4. В `ais.orders.v1` публикуется `OrderCreated`.
5. Executor Balancer принимает оба события.
6. Executor Balancer выбирает исполнителя.
7. Executor Balancer вызывает `POST /api/v1/assignments`.
8. AIS Simulator ждёт 2–10 секунд.
9. AIS Simulator сохраняет назначение и возвращает `200 OK`.
10. Повторный запрос с тем же `assignment_id` возвращает тот же результат без дубликата.
11. Назначение видно через `GET /api/v1/orders/{id}`.

До начала совместной интеграции оба разработчика должны подтвердить, что названия полей, событий, topics и HTTP endpoint совпадают с этим документом.
