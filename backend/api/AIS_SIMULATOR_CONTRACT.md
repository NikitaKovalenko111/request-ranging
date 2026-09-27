# Контракт интеграции с AIS Simulator

## 1. Назначение документа

Документ фиксирует контракт между следующими компонентами:

- AIS Simulator — источник заявок, исполнителей и бизнес-статусов;
- Decision Engine — фильтрация, расчёт признаков, ранжирование и балансировка;
- Executor Balancer — хранение истории, контроль целостности, резервирование и подтверждение назначения.

Сервисы не обращаются к базам данных друг друга. AIS передаёт заявки и сведения об исполнителях через Kafka. Executor Balancer отправляет выбранное назначение в AIS по HTTP.

Этот документ является нормативным для интеграции. Код сервисов необходимо привести к описанному здесь контракту.

## 2. Адреса и параметры окружения

| Компонент | Адрес |
|---|---|
| Executor Balancer | `http://localhost:8090` |
| AIS Simulator | `http://localhost:8091` |
| PostgreSQL Executor Balancer | `localhost:5442` |
| Redis | `localhost:6379` |
| Kafka | `localhost:9092` |

Основные параметры:

```text
KAFKA_BROKERS=kafka:9092
KAFKA_CONSUMER_GROUP=executor-balancer-v1
ORDER_TOPIC=ais.orders.v1
EXECUTOR_TOPIC=ais.executors.v1
EXECUTOR_REQUEST_TOPIC=executor-balancer.executor-requests.v1
DEAD_LETTER_TOPIC=executor-balancer.dead-letter.v1
ASSIGNMENT_DELAY_MIN=2s
ASSIGNMENT_DELAY_MAX=10s
ORDER_GENERATION_RATE=1.11
ORDER_GENERATION_TOTAL=10000
```

`EXECUTOR_REQUEST_TOPIC`, `ORDER_GENERATION_RATE` и `ORDER_GENERATION_TOTAL` — названия конфигурационных параметров, предложенные в этом документе. В ветке `simulation` готовых названий для Kafka-запроса начального снимка нет.

## 3. Каналы взаимодействия

| Направление | Канал | Назначение |
|---|---|---|
| AIS → Decision Engine и Executor Balancer | `ais.orders.v1` | создание и изменение заявок |
| AIS → Decision Engine и Executor Balancer | `ais.executors.v1` | снимок и изменения исполнителей |
| Executor Balancer → AIS | `executor-balancer.executor-requests.v1` | запрос актуального снимка активных исполнителей |
| Executor Balancer → AIS | HTTP `POST /api/v1/assignments` | подтверждение выбранного назначения |
| Executor Balancer → Kafka | `executor-balancer.dead-letter.v1` | сообщения, которые невозможно обработать |

Executor Balancer не должен загружать исполнителей через HTTP. Первоначальная синхронизация и все последующие изменения исполнителей выполняются через Kafka.

## 4. Общий формат Kafka-события AIS

События заявок и исполнителей имеют общий envelope:

```json
{
  "event_id": "9ba08c58-4037-4480-a45a-f90a033ab7db",
  "event_type": "OrderCreated",
  "event_version": 1,
  "occurred_at": "2026-09-27T10:00:00Z",
  "source": "ais-simulator",
  "payload": {}
}
```

Правила:

- `event_id` — UUID события;
- при повторной отправке одного события сохраняется прежний `event_id`;
- `event_type` определяет содержимое `payload`;
- `event_version` для первой версии равен `1`;
- `occurred_at` передаётся в UTC по RFC 3339;
- `source` для событий AIS равен `ais-simulator`;
- события одной заявки публикуются с Kafka key, равным `order_id`;
- события одного исполнителя публикуются с Kafka key, равным `executor_id`;
- событие считается обработанным только после успешного сохранения;
- повторное событие с тем же `event_id` не должно повторно менять состояние.

## 5. Модель заявки

`order_id` во всех сервисах имеет строковый тип. Decision Engine обязан вернуть тот же идентификатор без преобразования в число.

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

| Поле | Тип | Обязательное | Назначение |
|---|---|---|---|
| `order_id` | string | да | уникальный идентификатор заявки |
| `parent_id` | string или null | да | идентификатор предыдущей заявки после доработки |
| `status` | string | да | бизнес-статус заявки |
| `weight` | number > 0 | да | готовый вес заявки |
| `version` | integer > 0 | да | версия состояния заявки |
| `attributes.sum` | integer | да | сумма заявки |
| `attributes.order_type` | string | да | тип заявки |
| `attributes.subject` | string | да | тематика |
| `attributes.vip` | boolean | да | признак VIP |
| `attributes.client_msp` | string | нет | категория клиента |
| `attributes.executor_msp` | string | нет | требуемая категория исполнителя |
| `attributes.text` | string | нет | текст заявки |
| `attributes.region` | string | нет | регион |

На текущем этапе Executor Balancer использует `weight` напрямую. Отдельного поля `complexity` в контракте нет, и Go-сервис не пересчитывает вес.

## 6. Статусы заявки

| Статус | Значение |
|---|---|
| `processed` | заявка ожидает назначения или находится в работе |
| `await` | заявка возвращена на доработку |
| `accept` | заявка успешно завершена |
| `reject` | заявка завершена отказом |

Допустимый основной жизненный цикл:

```text
processed → accept
processed → reject
processed → await
await → новая заявка со статусом processed и новым order_id
```

После перехода в `await` старая заявка не возвращается в `processed`. AIS создаёт новую заявку, у которой `parent_id` равен `order_id` старой заявки.

`accept`, `reject` и `await` означают завершение работы с текущей заявкой. Получив такое событие, Executor Balancer освобождает нагрузку назначенного исполнителя. Если назначение для заявки отсутствует, событие сохраняется, но нагрузка не изменяется.

## 7. События заявок

### 7.1. `OrderCreated`

Публикуется после сохранения новой заявки.

```json
{
  "event_id": "9ba08c58-4037-4480-a45a-f90a033ab7db",
  "event_type": "OrderCreated",
  "event_version": 1,
  "occurred_at": "2026-09-27T10:00:00Z",
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

### 7.2. `OrderUpdated`

Публикуется после изменения веса или атрибутов. `payload` содержит полный актуальный снимок заявки в формате из раздела 5.

При каждом фактическом изменении `version` увеличивается на единицу. Событие со старой или равной версией не должно откатывать сохранённое состояние.

### 7.3. `OrderStatusChanged`

```json
{
  "event_id": "39212981-6db7-44ec-ae15-df2c70ca1dd2",
  "event_type": "OrderStatusChanged",
  "event_version": 1,
  "occurred_at": "2026-09-27T10:10:00Z",
  "source": "ais-simulator",
  "payload": {
    "order_id": "order-1032",
    "previous_status": "processed",
    "status": "accept",
    "version": 2
  }
}
```

Событие публикуется только после сохранения нового статуса в AIS.

## 8. Генерация 10 000 заявок

AIS не должен создавать или публиковать все 10 000 заявок одним пакетом при запуске.

Требуемое поведение:

- заявки создаются последовательно;
- после сохранения каждой заявки публикуется отдельное событие `OrderCreated`;
- средняя скорость — `1,11` заявки в секунду;
- примерный интервал между заявками — `900` миллисекунд;
- генерация останавливается после создания 10 000 заявок;
- Kafka key каждой заявки равен её строковому `order_id`;
- порядок событий одной заявки сохраняется.

При скорости `1,11` заявки в секунду полная генерация занимает примерно 2 часа 30 минут.

Формат идентификатора может быть таким:

```text
order-000001
order-000002
...
order-010000
```

Формат выше придуман в этом документе, потому что отдельное правило формирования `order_id` не было согласовано. Существенное требование — уникальный строковый идентификатор.

## 9. Модель исполнителя

```json
{
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
```

| Поле | Тип | Обязательное | Назначение |
|---|---|---|---|
| `executor_id` | string | да | уникальный идентификатор |
| `active` | boolean | да | может ли исполнитель участвовать в распределении |
| `capacity` | number > 0 | да | текущая пропускная способность, предоставляемая AIS |
| `daily_limit` | integer или null | нет | временно игнорируется Executor Balancer |
| `version` | integer > 0 | да | версия состояния исполнителя |
| `attributes` | object | да | параметры допустимых заявок |

Для первой версии `capacity` приходит готовой из AIS. Executor Balancer не рассчитывает медиану, график доступности или другое значение capacity. Он сохраняет полученное значение в PostgreSQL и Redis.

`daily_limit` может оставаться в событиях для совместимости с текущим AIS, но Executor Balancer не применяет его при выборе, резервировании и подсчёте нагрузки.

Текущая нагрузка не приходит из AIS. Executor Balancer самостоятельно хранит в Redis:

```text
current_load
active_count
pending_count
processed_today
last_assignment_at
```

## 10. Первоначальная загрузка исполнителей через Kafka

При запуске Executor Balancer запрашивает у AIS полный актуальный снимок активных исполнителей через Kafka. HTTP API исполнителей для этого не используется.

В ветке `simulation` готового Kafka request/response-контракта для снимка нет. Поэтому следующий формат является придуманным проектным решением и должен быть одинаково реализован в AIS и Executor Balancer.

### 10.1. Запрос снимка

Topic:

```text
executor-balancer.executor-requests.v1
```

Kafka key равен `request_id`.

```json
{
  "event_id": "e52a9097-77a6-41b5-9335-13bb97ccf3a0",
  "event_type": "ActiveExecutorsSnapshotRequested",
  "event_version": 1,
  "occurred_at": "2026-09-27T10:00:00Z",
  "source": "executor-balancer",
  "payload": {
    "request_id": "c1067ad4-8db9-49dc-a949-8d53a101d452"
  }
}
```

### 10.2. Ответ со снимком

AIS публикует ответ в `ais.executors.v1`. Kafka key равен `request_id`.

```json
{
  "event_id": "846c0b11-cadd-45f6-af17-15fb16e431a4",
  "event_type": "ActiveExecutorsSnapshot",
  "event_version": 1,
  "occurred_at": "2026-09-27T10:00:01Z",
  "source": "ais-simulator",
  "payload": {
    "request_id": "c1067ad4-8db9-49dc-a949-8d53a101d452",
    "executors": [
      {
        "executor_id": "executor-28",
        "active": true,
        "capacity": 1.5,
        "daily_limit": 100,
        "version": 3,
        "attributes": {
          "order_types": ["LEGAL_REVIEW"],
          "subjects": ["contract"],
          "vip_allowed": true,
          "regions": ["ural"]
        }
      }
    ]
  }
}
```

Правила обработки снимка:

- AIS включает только активных исполнителей;
- Executor Balancer выполняет замену своего набора активных исполнителей;
- все исполнители из снимка сохраняются или обновляются в PostgreSQL;
- активные исполнители добавляются в Redis;
- ранее активные исполнители, которых нет в снимке, удаляются из Redis, но не из PostgreSQL;
- runtime-поля уже известных исполнителей не должны обнуляться при обновлении метаданных;
- повторный снимок с тем же `request_id` обрабатывается идемпотентно.

## 11. Изменения исполнителей через Kafka

После начального снимка AIS публикует каждое изменение в `ais.executors.v1`.

### 11.1. `ExecutorCreated`

Содержит полный снимок нового исполнителя.

### 11.2. `ExecutorUpdated`

Содержит полный актуальный снимок после изменения активности, capacity или attributes.

```json
{
  "event_id": "3b7ea016-496c-440e-9137-3248c20561d9",
  "event_type": "ExecutorUpdated",
  "event_version": 1,
  "occurred_at": "2026-09-27T10:15:00Z",
  "source": "ais-simulator",
  "payload": {
    "executor_id": "executor-28",
    "active": false,
    "capacity": 1.5,
    "daily_limit": 100,
    "version": 4,
    "attributes": {
      "order_types": ["LEGAL_REVIEW"],
      "subjects": ["contract"],
      "vip_allowed": true,
      "regions": ["ural"]
    }
  }
}
```

Правила Executor Balancer:

- новая версия сохраняется в PostgreSQL;
- старая или равная версия игнорируется;
- активный исполнитель добавляется или обновляется в Redis;
- деактивированный исполнитель удаляется из Redis;
- деактивация не удаляет историю и запись PostgreSQL;
- `daily_limit` игнорируется;
- изменение capacity не должно обнулять текущую нагрузку.

## 12. HTTP API назначения

Используется фактический формат из ветки `simulation`.

### 12.1. Запрос

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
  "decided_at": "2026-09-27T10:00:01Z"
}
```

`Idempotency-Key` должен совпадать с `assignment_id`. AIS должен отклонять отсутствующий или несовпадающий ключ ответом `400`.

Перед успешным ответом AIS имитирует задержку от 2 до 10 секунд.

### 12.2. Успешный ответ

```http
200 OK
```

```json
{
  "assignment_id": "7a44af14-b17b-45e2-8cb9-f17690252e92",
  "order_id": "order-1032",
  "executor_id": "executor-28",
  "status": "confirmed",
  "confirmed_at": "2026-09-27T10:00:08Z"
}
```

После успешного назначения AIS сохраняет связь заявки с исполнителем.

### 12.3. Идемпотентность

Повторный запрос с тем же `assignment_id`:

- не создаёт повторное назначение;
- возвращает первоначальный результат;
- не обязан повторять искусственную задержку.

Один `order_id` может иметь только одно подтверждённое назначение. Проверка и сохранение должны быть защищены от двух параллельных запросов.

### 12.4. Ошибки

| HTTP-код | Значение | Действие Executor Balancer |
|---|---|---|
| `400` | некорректный запрос или Idempotency-Key | отменить reservation, не повторять |
| `404` | заявка или исполнитель не найдены | отменить reservation, не повторять |
| `409` | заявка уже назначена | отменить reservation, синхронизировать состояние |
| `422` | исполнитель неактивен или статус заявки запрещает назначение | отменить reservation, проверить следующего кандидата |
| `500` | внутренняя ошибка AIS | повторить запрос |
| `503` | временная недоступность AIS | повторить запрос |

Формат ошибки взят из ветки `simulation`:

```json
{
  "code": "ORDER_ALREADY_ASSIGNED",
  "message": "Order order-1032 is already assigned",
  "retryable": false
}
```

Параметры повторов Executor Balancer:

```text
тайм-аут одной попытки: 12 секунд
максимум попыток: 3
задержки: 500 мс, 1 секунда, 2 секунды
```

На всех попытках используются одинаковые `assignment_id` и `Idempotency-Key`.

### 12.5. Принудительная ошибка для интеграционных тестов

В ветке `simulation` детерминированного способа получить `500` или `503` нет. Для проверки повторов предлагается следующий придуманный тестовый контракт:

```http
POST /api/v1/assignments
X-Simulate-Status: 503
```

Допустимые значения заголовка: `500` и `503`. Заголовок используется только в локальном и тестовом окружении. AIS возвращает соответствующий код и стандартное тело ошибки, не создавая назначение:

```json
{
  "code": "SERVICE_TEMPORARILY_UNAVAILABLE",
  "message": "Simulated temporary AIS failure",
  "retryable": true
}
```

В production-подобном режиме заголовок должен быть отключён.

## 13. Разделение ответственности

AIS отвечает за:

- исходные данные заявки;
- строковый `order_id`;
- готовый `weight`;
- исполнителей, их активность, capacity и attributes;
- бизнес-статус заявки;
- подтверждение назначения;
- последовательную генерацию заявок со скоростью 1,11/с.

Decision Engine отвечает за:

- Rule Engine;
- Feature Extractor;
- ML Ranker;
- Balancer;
- формирование ранжированного списка кандидатов.

Executor Balancer отвечает за:

- локальное хранение заявок и исполнителей;
- хранение всех исполнителей в PostgreSQL;
- хранение активных исполнителей и runtime-нагрузки в Redis;
- контроль версий и повторных событий;
- атомарную резервацию кандидата;
- проверку `current_load + weight <= capacity`;
- хранение Assignment и Decision Trace;
- отправку назначения в AIS;
- подтверждение, отмену и истечение reservation;
- освобождение нагрузки при завершении заявки.

## 14. Интеграционный сценарий

1. Executor Balancer запускается и публикует `ActiveExecutorsSnapshotRequested`.
2. AIS публикует `ActiveExecutorsSnapshot` в `ais.executors.v1`.
3. Executor Balancer сохраняет исполнителей в PostgreSQL и Redis.
4. AIS последовательно создаёт заявки со скоростью 1,11/с.
5. Для каждой заявки AIS публикует `OrderCreated` в `ais.orders.v1`.
6. Decision Engine получает данные и публикует ранжированный список кандидатов.
7. Executor Balancer атомарно резервирует первого доступного кандидата.
8. Executor Balancer создаёт pending Assignment и Decision Trace.
9. Executor Balancer вызывает `POST /api/v1/assignments`.
10. AIS подтверждает назначение.
11. Executor Balancer переводит Assignment и reservation в confirmed.
12. При `accept`, `reject` или `await` AIS публикует `OrderStatusChanged`.
13. Executor Balancer освобождает нагрузку исполнителя.

## 15. Критерии готовности AIS к интеграции

- AIS подключается к Kafka и HTTP-порту `8091`;
- начальный снимок активных исполнителей передаётся только через Kafka;
- изменения исполнителей передаются через `ais.executors.v1`;
- `capacity` всегда больше нуля и приходит от AIS;
- `daily_limit` не влияет на распределение;
- `order_id` везде является строкой;
- `weight` передаётся готовым и используется без пересчёта;
- 10 000 заявок создаются и публикуются последовательно со скоростью 1,11/с;
- события содержат UUID, версию и RFC 3339 timestamp;
- `POST /api/v1/assignments` идемпотентен;
- два параллельных запроса не могут назначить одну заявку дважды;
- поддерживаются ответы `409` и `422`;
- для проверки повторов можно получить тестовые ответы `500` и `503`;
- после `await` создаётся новая заявка с `parent_id`;
- AIS не читает и не изменяет PostgreSQL или Redis Executor Balancer.

## 16. Явно придуманные части контракта

Следующей информации не было ни в переданных требованиях, ни в готовом коде ветки `simulation`, поэтому она предложена в этом документе:

1. Topic запроса снимка: `executor-balancer.executor-requests.v1`.
2. Событие запроса: `ActiveExecutorsSnapshotRequested`.
3. Событие ответа: `ActiveExecutorsSnapshot`.
4. Использование `request_id` для связи запроса и ответа.
5. Переменные `ORDER_GENERATION_RATE` и `ORDER_GENERATION_TOTAL`.
6. Пример последовательного формата `order-000001`.
7. Тестовый заголовок `X-Simulate-Status` для ответов `500` и `503`.

Форматы обычных событий заявок и исполнителей, HTTP-запрос назначения, успешный ответ и JSON ошибки основаны на существующих примерах ветки `simulation`, но приведены в соответствие с решениями из этого документа.
