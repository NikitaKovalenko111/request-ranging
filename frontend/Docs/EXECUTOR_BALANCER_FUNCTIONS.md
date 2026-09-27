# Executor Balancer --- функции системы

> MVP-функциональность для хакатона: 4 дня, команда 6 человек.

## 1. Общая функциональность

Основной pipeline:

``` text
External AIS
    ↓
Kafka
    ↓
Backend / Consumer
    ↓
LLM Extractor (опционально)
    ↓
Rule Engine
    ↓
Допустимые исполнители
    ↓
ML / Ranker
    ↓
Balancer
    ↓
Atomic Reservation (Redis)
    ↓
Assignment
    ↓
External AIS
```

Система должна:

-   принимать заявки из внешней АИС;
-   получать и обновлять данные исполнителей;
-   поддерживать динамические правила распределения;
-   фильтровать исполнителей по обязательным условиям;
-   ранжировать подходящих исполнителей;
-   учитывать текущую и ожидающую подтверждения нагрузку;
-   справедливо распределять заявки;
-   предотвращать race conditions;
-   учитывать суточные лимиты;
-   поддерживать веса заявок и исполнителей;
-   обрабатывать повторные заявки (`parent_id`);
-   отправлять назначение обратно во внешнюю АИС;
-   хранить историю решений;
-   отображать распределение и метрики на dashboard;
-   объяснять, почему был выбран конкретный исполнитель.

------------------------------------------------------------------------

## 2. Frontend

### 2.1. Dashboard

Функции:

-   отображение общего количества поступивших заявок;
-   отображение количества назначенных и неназначенных заявок;
-   количество активных исполнителей;
-   отображение средней скорости назначения;
-   отображение `p95` времени назначения;
-   отображение текущей нагрузки исполнителей;
-   отображение `confirmed` и `pending` нагрузки;
-   график заявок по времени;
-   график назначений по времени;
-   график распределения нагрузки;
-   отображение fairness;
-   live-таблица последних назначений;
-   отображение ошибок распределения;
-   отображение заявок без подходящих исполнителей;
-   автоматическое обновление через WebSocket/SSE/polling.

### 2.2. Rule Constructor

Функции:

-   просмотр правил;
-   создание правила;
-   редактирование правила;
-   удаление правила;
-   включение/выключение правила;
-   выбор поля заявки;
-   выбор оператора;
-   выбор поля исполнителя или константы;
-   изменение приоритета правила;
-   проверка правила на тестовой заявке;
-   отображение причины `PASS/FAIL`.

Поддерживаемые операции MVP:

``` text
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

### 2.3. Orders / Assignment Inspector

Функции:

-   список заявок;
-   фильтрация по статусу;
-   просмотр параметров заявки;
-   просмотр назначенного исполнителя;
-   просмотр количества первоначальных кандидатов;
-   просмотр кандидатов после Rule Engine;
-   просмотр ranking score;
-   просмотр нагрузки кандидатов;
-   отображение выбранного исполнителя;
-   отображение времени принятия решения;
-   отображение полного Decision Trace.

### 2.4. Executors

Функции:

-   список исполнителей;
-   просмотр параметров;
-   отображение `ACTIVE/INACTIVE`;
-   изменение статуса;
-   отображение квалификации;
-   отображение текущих заявок;
-   отображение `pending` заявок;
-   отображение суточного лимита;
-   отображение текущего `daily_count`;
-   отображение weighted load;
-   просмотр истории назначений.

------------------------------------------------------------------------

## 3. Backend (Go)

Backend является orchestration layer системы.

### 3.1. REST API

Минимальные endpoints:

``` text
POST   /orders
GET    /orders
GET    /orders/{id}

GET    /executors
GET    /executors/{id}
POST   /executors
PATCH  /executors/{id}

GET    /rules
POST   /rules
PUT    /rules/{id}
DELETE /rules/{id}

GET    /assignments
GET    /assignments/{orderId}

GET    /dashboard
GET    /metrics
```

### 3.2. Orders

Функции:

-   получение заявки;
-   валидация;
-   сохранение;
-   обновление статуса;
-   поиск по `id`;
-   поиск родительской заявки;
-   запуск процесса распределения;
-   защита от повторной обработки.

### 3.3. Executors

Функции:

-   получение списка исполнителей;
-   создание/обновление исполнителя;
-   синхронизация с АИС;
-   изменение активности;
-   получение настроек;
-   обновление runtime-state;
-   получение активных исполнителей.

### 3.4. DistributionService

Главный pipeline:

``` text
Order
  ↓
Parent Handler
  ↓
Get Executors
  ↓
RuleEngine.Filter()
  ↓
Ranker.Rank()
  ↓
Balancer.Select()
  ↓
Reservation.TryReserve()
  ↓
Create Assignment
  ↓
Send to AIS
```

Функции:

-   запуск распределения;
-   обработка отсутствия кандидатов;
-   вызов Rule Engine;
-   вызов Ranker;
-   вызов Balancer;
-   резервирование исполнителя;
-   retry при конфликте;
-   сохранение результата;
-   отправка результата в АИС;
-   создание Decision Trace;
-   сбор метрик.

------------------------------------------------------------------------

## 4. Kafka

Kafka используется как транспорт событий между АИС и Backend.

### События

``` text
OrderCreated
OrderUpdated
OrderStatusChanged
ExecutorUpdated
```

Опционально:

``` text
AssignmentCreated
```

### Функции

-   публикация событий;
-   получение событий;
-   сериализация/десериализация;
-   валидация события;
-   retry;
-   acknowledgement;
-   обработка ошибок;
-   deduplication;
-   защита от повторной обработки одного `event_id/order_id`.

------------------------------------------------------------------------

## 5. Rule Engine

Задача Rule Engine:

> определить, каким исполнителям заявку вообще разрешено назначать.

### Функции

-   загрузка активных правил;
-   проверка активности исполнителя;
-   проверка суточного лимита;
-   проверка диапазона суммы;
-   проверка типа заявки;
-   проверка тематики;
-   проверка VIP;
-   проверка массивов/справочников;
-   выполнение динамических правил;
-   фильтрация списка исполнителей;
-   формирование причины отклонения;
-   сохранение результатов проверки для Decision Trace.

Интерфейс:

``` text
Filter(order, executors, rules)
    →
eligibleExecutors
```

Rule Engine отвечает только на вопрос:

> **Можно ли назначить заявку этому исполнителю?**

------------------------------------------------------------------------

## 6. ML / Ranker

Задача:

> ранжировать уже допустимых исполнителей по пригодности к конкретной
> заявке.

### Вход

``` text
Order Features
+
Executor Features
+
LLM Tags
+
Historical Features
```

### Выход

``` text
Executor A → 0.91
Executor B → 0.84
Executor C → 0.71
```

### Функции

-   подготовка features;
-   формирование признаков пары `order-executor`;
-   получение score;
-   сортировка кандидатов;
-   формирование Top-K;
-   возврат ranking результатов;
-   логирование версии модели;
-   сохранение score для Decision Trace.

### Возможные реализации

MVP:

``` text
HeuristicRanker
```

Расширение:

``` text
CatBoost
LightGBM
XGBoost
Learning-to-Rank
```

Ranker отвечает на вопрос:

> **Насколько хорошо этот исполнитель подходит к заявке?**

------------------------------------------------------------------------

## 7. LLM Extractor

LLM не назначает исполнителя.

Задача:

> преобразовать неструктурированный текст заявки в структурированные
> признаки.

Пример:

``` text
"Срочная проверка договора с иностранным контрагентом"
```

Результат:

``` json
{
  "domain": "legal",
  "urgency": "high",
  "foreign_counterparty": true,
  "complexity": "high"
}
```

### Функции

-   получение текста;
-   извлечение тегов;
-   structured output;
-   проверка schema;
-   нормализация значений;
-   сохранение extraction;
-   передача признаков Ranker;
-   обработка timeout/error;
-   fallback без LLM.

LLM должен быть **опциональным**: при его недоступности основное
распределение продолжает работать.

------------------------------------------------------------------------

## 8. Balancer

Задача:

> выбрать среди подходящих кандидатов исполнителя с учётом нагрузки и
> справедливости.

### Учитываемые параметры

-   `confirmed_weight`;
-   `pending_weight`;
-   `executor_weight/capacity`;
-   количество открытых заявок;
-   время последнего назначения;
-   fairness;
-   ranking результата.

Базовая оценка нагрузки:

``` text
effective_load =
    (confirmed_weight + pending_weight)
    / executor_weight
```

### Функции

-   расчёт effective load;
-   сравнение нагрузки кандидатов;
-   выбор кандидата;
-   использование Top-K Ranker;
-   tie-breaking;
-   учёт времени последнего назначения;
-   расчёт fairness;
-   возврат следующего кандидата при невозможности reservation.

Balancer отвечает на вопрос:

> **Кому из подходящих исполнителей справедливее назначить заявку
> сейчас?**

------------------------------------------------------------------------

## 9. Reservation / Concurrency

Задача:

> исключить race conditions при параллельной обработке заявок.

### Функции

``` text
TryReserve()
ConfirmReservation()
CancelReservation()
ExpireReservation()
```

При резервировании:

``` text
Balancer выбрал Executor
        ↓
Atomic TryReserve
        ↓
pending_weight += order.weight
        ↓
SUCCESS / FAIL
```

При конфликте:

``` text
FAIL
 ↓
следующий кандидат
 ↓
TryReserve()
```

Требования:

-   атомарность;
-   отсутствие двойного назначения;
-   timeout reservation;
-   rollback при ошибке АИС;
-   корректная обработка параллельных заявок.

------------------------------------------------------------------------

## 10. Redis

Redis хранит оперативное состояние.

### Данные

``` text
executor:{id}:active
executor:{id}:confirmed_weight
executor:{id}:pending_weight
executor:{id}:daily_count
executor:{id}:last_assignment
```

Также:

``` text
reservations
locks
executor cache
active rules cache
```

### Функции

-   получение active executors;
-   получение текущей нагрузки;
-   атомарное резервирование;
-   подтверждение reservation;
-   rollback;
-   обновление runtime-state;
-   инкремент/декремент нагрузки;
-   кеширование исполнителей.

------------------------------------------------------------------------

## 11. PostgreSQL

PostgreSQL --- постоянное хранилище сервиса.

### Основные таблицы

``` text
orders
executors
executor_settings
rules
assignments
assignment_candidates
llm_extractions
metrics
```

### Функции

-   хранение заявок;
-   хранение исполнителей;
-   хранение настроек;
-   хранение правил;
-   хранение назначений;
-   хранение истории решений;
-   хранение ranking результатов;
-   хранение LLM extraction;
-   хранение аналитических данных;
-   получение данных для dashboard.

------------------------------------------------------------------------

## 12. Parent Order Handler

Обработка повторных заявок.

Алгоритм:

``` text
parent_id == null
    ↓
обычное распределение
```

``` text
parent_id != null
    ↓
найти parent
    ↓
получить previous_executor
    ↓
ACTIVE?
    ↓
соответствует параметрам?
    ↓
YES → вернуть previous_executor
NO  → обычное распределение
```

При возврате заявки предыдущему исполнителю суточный лимит не
учитывается в соответствии с условием кейса.

### Функции

-   поиск parent;
-   получение прошлого исполнителя;
-   проверка активности;
-   проверка hard rules;
-   исключение daily limit для данного сценария;
-   возврат в стандартный pipeline при невозможности повторного
    назначения.

------------------------------------------------------------------------

## 13. Fake AIS

Fake AIS эмулирует внешнюю информационную систему.

### API

``` text
POST   /orders
GET    /orders/{id}
PATCH  /orders/{id}

GET    /executors
POST   /executors
PATCH  /executors/{id}

POST   /assignments
```

### Функции

-   CRUD заявок;
-   CRUD исполнителей;
-   CRUD настроек;
-   отправка новых заявок в Kafka;
-   получение назначения;
-   изменение статуса заявки;
-   эмуляция задержки подтверждения 2--10 секунд.

------------------------------------------------------------------------

## 14. Order Generator

Генератор нагрузки.

### Функции

-   генерация случайных заявок;
-   настройка скорости;
-   генерация разных типов;
-   генерация разных весов;
-   генерация VIP;
-   генерация parent-заявок;
-   генерация текстового описания;
-   burst-нагрузка.

Режимы:

``` text
1 order/sec
10 orders/sec
100 orders/sec
BURST 500
BURST 1000
```

------------------------------------------------------------------------

## 15. Executor Simulator

Эмулирует работу исполнителей.

### Функции

-   перевод заявки в обработку;
-   завершение заявки;
-   `accept`;
-   `reject`;
-   `await`;
-   освобождение рабочего слота;
-   уменьшение текущей нагрузки;
-   создание повторной заявки после `await`;
-   случайное изменение статуса исполнителя;
-   эмуляция разной скорости работы.

------------------------------------------------------------------------

## 16. Analytics / Metrics

### Метрики системы

``` text
total_orders
assigned_orders
unassigned_orders
orders_per_second

avg_assignment_time
p95_assignment_time

active_executors
pending_assignments

rule_rejections
reservation_conflicts
errors
```

### Метрики распределения

``` text
orders_per_executor
weighted_load_per_executor
average_load
load_deviation
fairness
```

### ML-метрики (если ML реализован)

``` text
rank_score
Top-K
reassignment_rate
successful_assignment_rate
```

### Функции

-   сбор метрик;
-   агрегация;
-   хранение;
-   API для dashboard;
-   расчёт fairness;
-   расчёт распределения нагрузки;
-   обновление метрик в near real-time.

------------------------------------------------------------------------

## 17. Explainability / Decision Trace

Для каждого назначения система должна уметь ответить:

> Почему выбран именно этот исполнитель?

Пример:

``` text
Order #1032

50 исполнителей
      ↓
41 ACTIVE
      ↓
8 прошли Rule Engine
      ↓
3 вошли в Top-K Ranker
      ↓
Balancer сравнил нагрузку
      ↓
Executor #28 selected
```

### Сохраняемые данные

``` text
order_id
total_executors
active_executors
eligible_executors

failed_rules

ranker_scores
top_k

load_before_assignment

selected_executor
selection_reason

processing_time
timestamp
```

### Функции

-   сбор этапов решения;
-   хранение Decision Trace;
-   API получения trace;
-   визуализация на frontend.

------------------------------------------------------------------------

## 18. Feedback --- дополнительная функция

Не является обязательной для основного MVP.

### Функции

-   оценка назначения `1–5`;
-   указание причины оценки;
-   сохранение feedback;
-   связывание feedback с заявкой;
-   связывание с executor;
-   связывание с версией Ranker;
-   использование данных для будущего обучения.

Примеры причин:

``` text
Не моя специализация
Недостаточная квалификация
Слишком высокая сложность
Исполнитель был перегружен
Неверно определена тематика
Личная предпочтительность
Другое
```

------------------------------------------------------------------------

## 19. Model Lifecycle --- Roadmap

Не является P0 для четырёхдневного MVP.

В дальнейшем:

``` text
Feedback + Outcomes
        ↓
Training Dataset
        ↓
Train Challenger
        ↓
Offline Evaluation
        ↓
Shadow
        ↓
A/B Test
        ↓
Promote / Reject
```

Функции:

-   версионирование моделей;
-   Champion/Challenger;
-   offline evaluation;
-   shadow mode;
-   A/B;
-   disagreement set;
-   rollback;
-   promotion;
-   feature schema versioning.

------------------------------------------------------------------------

# 20. Приоритет реализации

## P0 --- система должна работать

``` text
Fake AIS
Kafka
Go Backend
PostgreSQL
Rule Engine
Balancer
Redis
Atomic Reservation
Parent Order Handler
Assignment → AIS
```

## P1 --- сильное демо

``` text
Rule Constructor
Dashboard
Order Generator
Executor Simulator
Decision Trace
Analytics
Burst Test
```

## P2 --- AI

``` text
Heuristic / ML Ranker
LLM Extractor
Feedback
```

## Roadmap

``` text
Champion / Challenger
Shadow Mode
A/B Testing
Feature Discovery
Embeddings
Automatic Retraining
Model Registry
```

------------------------------------------------------------------------

# 21. Ответственность блоков в одной схеме

``` text
Frontend
    → управление и визуализация

Kafka
    → доставка событий

Backend
    → orchestration

Rule Engine
    → МОЖНО ли назначить?

ML Ranker
    → НАСКОЛЬКО подходит?

Balancer
    → КОМУ справедливее назначить сейчас?

Redis / Reservation
    → МОЖНО ли безопасно зафиксировать выбор?

PostgreSQL
    → что произошло и почему?

Fake AIS
    → внешний источник заявок и состояний

Analytics
    → насколько хорошо работает система?

Decision Trace
    → почему система приняла это решение?
```

## Итоговый runtime pipeline

``` text
Fake AIS
   ↓
Kafka
   ↓
Go Backend
   ↓
Parent Handler
   ↓
LLM Extractor (optional)
   ↓
Rule Engine
   ↓
ML / Heuristic Ranker
   ↓
Balancer
   ↓
Redis Atomic Reservation
   ↓
Assignment
   ↓
Fake AIS
   ↓
Confirmation / Status Change
   ↓
Redis + PostgreSQL
   ↓
Dashboard / Analytics
```
