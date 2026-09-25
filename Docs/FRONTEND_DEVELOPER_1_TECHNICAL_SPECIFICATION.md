# Техническое задание на frontend контур мониторинга и объяснимости Executor Balancer

## 1. Общие сведения

### 1.1. Наименование работ

Разработка frontend-контура мониторинга, просмотра заявок и объяснения решений системы Executor Balancer.

### 1.2. Срок выполнения

Срок реализации — 4 календарных дня хакатона.

### 1.3. Место работ в проекте

Frontend разрабатывается командой из двух человек.

Настоящее техническое задание определяет область ответственности первого frontend-разработчика:

- Dashboard;
- Orders;
- Order Details;
- Decision Trace;
- визуализация нагрузки и метрик;
- polling и обновление данных;
- экспорт отчёта;
- Layout, Sidebar, Header, router и StatusBadge.

Связанный контур второго frontend-разработчика включает Executors, Rules, Rule Constructor, Test Rule, API client, QueryClient и общие правила форм.

## 2. Цели работ

Результат работ должен обеспечивать:

1. отображение общего состояния системы;
2. отображение количества поступивших, назначенных и неназначенных заявок;
3. отображение активных исполнителей;
4. отображение средней и p95 задержки назначения;
5. отображение confirmed и pending нагрузки;
6. отображение динамики заявок и назначений;
7. отображение fairness;
8. просмотр списка заявок;
9. просмотр параметров конкретной заявки;
10. просмотр назначенного исполнителя;
11. просмотр полного Decision Trace;
12. отображение причин исключения каждого кандидата;
13. отображение ranking score и effective load;
14. отображение результата обработки parent_id;
15. обновление данных с минимальной задержкой;
16. экспорт метрик и назначений после готовности обязательного сценария.

## 3. Границы работ

### 3.1. Функции, входящие в обязательный объём

- основной Layout;
- Sidebar;
- Header;
- router;
- StatusBadge;
- Dashboard;
- KPI-карточки;
- минимум один график динамики;
- график confirmed и pending нагрузки;
- таблица последних назначений;
- Orders;
- фильтрация заявок;
- Order Details;
- Decision Trace;
- отображение parent_id;
- API-модули Dashboard, Metrics, Orders и Assignments;
- доменные типы Order, Assignment, Dashboard и Decision Trace;
- доменные моки;
- polling через TanStack Query;
- Loading, Error, Empty и Success;
- отображение времени последнего обновления;
- адаптивность для демонстрационного разрешения.

### 3.2. Функции, не входящие в обязательный объём

- самостоятельный расчёт бизнес-метрик как источника истины;
- самостоятельное выполнение Rule Engine;
- самостоятельное ранжирование кандидатов;
- самостоятельный выбор исполнителя;
- реализация атомарного резервирования;
- WebSocket как обязательный транспорт;
- редактирование заявок;
- редактирование исполнителей;
- редактирование правил;
- сложный конструктор пользовательских отчётов;
- обязательная тёмная тема;
- сложные анимации;
- ML-интерпретация сверх данных Decision Trace;
- карта или сетевой граф алгоритма.

### 3.3. Функции второй очереди

- Excel-экспорт;
- CSV-экспорт;
- дополнительные графики;
- график ошибок;
- отображение reservation conflicts;
- выбор периода;
- SSE или WebSocket;
- расширенная аналитика исполнителя;
- сохранённые представления фильтров.

## 4. Требования исходного кейса

Frontend-контур должен наглядно подтверждать:

- обработку большого потока заявок;
- распределение с минимальной задержкой;
- учёт активных исполнителей;
- соответствие параметрам заявки;
- учёт суточного лимита;
- учёт веса заявки;
- учёт веса исполнителя;
- учёт confirmed и pending нагрузки;
- работу в асинхронном окне подтверждения 2–10 секунд;
- справедливость распределения;
- обработку повторных заявок через parent_id;
- объяснимость выбора исполнителя;
- реакцию системы на изменение правил и активности исполнителей.

Frontend должен визуализировать результаты backend, но не подменять backend-расчёты.

## 5. Общая архитектура frontend

### 5.1. Технологический стек

- Vite;
- React;
- TypeScript;
- React Router;
- TanStack Query;
- готовый UI-kit;
- библиотека графиков;
- TanStack Table при необходимости;
- SheetJS или CSV для экспорта;
- Vitest и React Testing Library при наличии времени.

### 5.2. Структура проекта

~~~text
src/
├── app/
│   ├── App.tsx
│   ├── router.tsx
│   ├── providers.tsx
│   └── queryClient.ts
├── api/
│   ├── client.ts
│   ├── errors.ts
│   ├── dataSource.ts
│   ├── dashboard.ts
│   ├── orders.ts
│   ├── assignments.ts
│   ├── executors.ts
│   └── rules.ts
├── features/
│   ├── dashboard/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── model/
│   │   └── pages/
│   ├── orders/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── model/
│   │   └── pages/
│   ├── decision-trace/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── model/
│   ├── executors/
│   └── rules/
├── shared/
│   ├── components/
│   ├── config/
│   ├── format/
│   ├── hooks/
│   └── types/
├── mocks/
│   ├── dashboard.ts
│   ├── orders.ts
│   ├── assignments.ts
│   ├── executors.ts
│   ├── rules.ts
│   └── ruleSchema.ts
└── types/
    ├── api.ts
    ├── dashboard.ts
    ├── order.ts
    ├── assignment.ts
    ├── executor.ts
    └── rule.ts
~~~

Доменные модули должны быть разделены. Компоненты не должны импортировать моки напрямую.

## 6. Общие компоненты и соглашения

### 6.1. Общие компоненты

В проекте должны использоваться единые:

- Layout;
- Sidebar;
- Header;
- StatusBadge;
- LoadingState;
- ErrorState;
- EmptyState;
- ConfirmDialog;
- Button;
- Input;
- Select;
- Dialog;
- Drawer;
- Tooltip;
- Toast;
- форматтер даты;
- форматтер длительности;
- форматтер чисел;
- форматтер процентов;
- форматтер нагрузки.

Дублирование общих компонентов не допускается.

### 6.2. Владение общими файлами

Контур первого frontend-разработчика является владельцем:

- router;
- Layout;
- Sidebar;
- Header;
- StatusBadge;
- основной навигации;
- responsive shell;
- общих форматтеров даты и длительности.

Контур второго frontend-разработчика является владельцем:

- api/client.ts;
- api/errors.ts;
- api/dataSource.ts;
- QueryClient;
- React Hook Form conventions;
- Zod conventions;
- form wrappers;
- переменных окружения;
- переключения mock/API.

Изменение общего файла выполняется его владельцем или после предварительного согласования.

### 6.3. Общие маршруты

~~~text
/dashboard
/orders
/executors
/rules
~~~

Дополнительный маршрут:

~~~text
/orders/:id
~~~

Order Details и Decision Trace могут быть реализованы через отдельную страницу, Drawer или Modal. Для демонстрации предпочтителен Drawer или страница с устойчивой прямой ссылкой.

### 6.4. Переменные окружения

~~~text
VITE_API_BASE_URL=http://localhost:8080/api/v1
VITE_DATA_SOURCE=mock
VITE_POLL_INTERVAL_MS=2000
~~~

Допустимые источники данных:

~~~text
mock
api
~~~

Автоматическая подмена упавшего API моками не допускается.

### 6.5. Именование

- TypeScript-поля — camelCase;
- компоненты — PascalCase;
- хуки — useSomething;
- значения технических enum — UPPER_SNAKE_CASE, кроме статусов заявки из исходного кейса;
- даты — ISO 8601;
- query keys — массивы;
- преобразование backend DTO выполняется в API-адаптере;
- единицы измерения фиксируются в названии поля.

## 7. Общие API-типы

Файл:

~~~text
src/types/api.ts
~~~

~~~ts
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  fieldErrors?: Record<string, string>;
  traceId?: string;
}

export interface PaginationMeta {
  limit: number;
  offset: number;
  total: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}
~~~

Рекомендуемый формат ошибки:

~~~json
{
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "Order 1032 was not found",
    "traceId": "req-72f4a1"
  }
}
~~~

Обработка:

| Код | Требуемое поведение |
|---|---|
| 400 | сообщение о некорректных фильтрах |
| 404 | состояние «Заявка не найдена» |
| 409 | отображение конфликта |
| 422 | доменная ошибка |
| 500 | Error State и traceId |
| Network error | сообщение о недоступности backend |

## 8. Общие сущности

## 8.1. Order

~~~ts
export type OrderStatus =
  | 'processed'
  | 'await'
  | 'accept'
  | 'reject';

export type AssignmentStatus =
  | 'pending'
  | 'reserved'
  | 'assigned'
  | 'unassigned'
  | 'failed';

export interface Order {
  id: number;
  parentId: number | null;
  assignedExecutorId: number | null;
  sum: number | null;
  clientMsp: string | null;
  executorMsp: string | null;
  orderType: string;
  subject: string;
  vip: boolean;
  weight: number;
  text: string;
  status: OrderStatus;
  assignmentStatus: AssignmentStatus;
  createdAt: string;
  assignedAt: string | null;
  processingTimeMs: number | null;
}

export interface OrderOption {
  id: number;
  label: string;
  status: OrderStatus;
  vip: boolean;
}
~~~

Статус жизненного цикла заявки и статус назначения должны храниться отдельно.

## 8.2. Executor

Тип принадлежит контуру второго frontend-разработчика и повторно не объявляется.

~~~ts
export type ExecutorStatus = 'ACTIVE' | 'INACTIVE';

export interface ExecutorSummary {
  id: number;
  displayName: string;
  status: ExecutorStatus;
  qualification: string | null;
  capacityWeight: number;
  confirmedWeight: number;
  pendingWeight: number;
  effectiveLoad: number;
  dailyCount: number;
  maxDailyLimit: number | null;
}
~~~

## 8.3. Assignment

~~~ts
export interface Assignment {
  orderId: number;
  executorId: number | null;
  executorName: string | null;
  status: AssignmentStatus;
  createdAt: string;
  reservedAt: string | null;
  confirmedAt: string | null;
  processingTimeMs: number | null;
  explanation: string | null;
}
~~~

## 8.4. Dashboard

~~~ts
export interface DashboardSummary {
  periodFrom: string;
  periodTo: string;
  generatedAt: string;
  totalOrders: number;
  assignedOrders: number;
  unassignedOrders: number;
  failedOrders: number;
  activeExecutors: number;
  pendingAssignments: number;
  ordersPerSecond: number;
  averageAssignmentTimeMs: number;
  p95AssignmentTimeMs: number;
  ruleRejections: number;
  reservationConflicts: number;
  errors: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  orders: number;
  assignments: number;
  failures: number;
}

export interface ExecutorLoadMetric {
  executorId: number;
  executorName: string;
  capacityWeight: number;
  confirmedWeight: number;
  pendingWeight: number;
  effectiveLoad: number;
  dailyCount: number;
  maxDailyLimit: number | null;
}

export type FairnessMetricKind =
  | 'JAIN_INDEX'
  | 'DEVIATION_PERCENT';

export interface FairnessMetric {
  kind: FairnessMetricKind;
  value: number;
  target: number | null;
  description: string;
}

export interface DashboardData {
  summary: DashboardSummary;
  timeline: TimeSeriesPoint[];
  executorLoads: ExecutorLoadMetric[];
  fairness: FairnessMetric;
  latestAssignments: Assignment[];
}
~~~

Jain Index и процентное отклонение являются разными метриками. UI должен отображать точное название, значение и описание, полученные с backend.

## 8.5. Decision Trace

~~~ts
export type ReservationResult =
  | 'SUCCESS'
  | 'CONFLICT'
  | 'SKIPPED';

export interface FailedRule {
  ruleId: string | null;
  ruleName: string | null;
  reason: string;
}

export interface CandidateDecision {
  executorId: number;
  executorName: string;
  active: boolean;
  passedRules: boolean;
  failedRules: FailedRule[];
  dailyLimitReached: boolean;
  rankScore: number | null;
  confirmedWeight: number;
  pendingWeight: number;
  effectiveLoad: number;
  reservationResult: ReservationResult;
  selected: boolean;
}

export interface ParentReuseDecision {
  attempted: boolean;
  parentOrderId: number | null;
  previousExecutorId: number | null;
  previousExecutorName: string | null;
  previousExecutorActive: boolean | null;
  parametersMatched: boolean | null;
  dailyLimitIgnored: boolean;
  reused: boolean;
  reason: string | null;
}

export interface DecisionStage {
  code:
    | 'TOTAL'
    | 'ACTIVE'
    | 'RULE_ENGINE'
    | 'RANKING'
    | 'BALANCING'
    | 'RESERVATION'
    | 'ASSIGNMENT';
  label: string;
  inputCount: number;
  outputCount: number;
  durationMs: number | null;
}

export interface DecisionTrace {
  orderId: number;
  timestamp: string;
  processingTimeMs: number;
  modelVersion: string | null;
  rulesVersion: string | null;
  totalExecutors: number;
  activeExecutors: number;
  eligibleExecutors: number;
  topKExecutors: number | null;
  selectedExecutorId: number | null;
  explanation: string;
  stages: DecisionStage[];
  parentReuse: ParentReuseDecision;
  candidates: CandidateDecision[];
}
~~~

Frontend не должен создавать отсутствующие этапы или причины. Если backend не вернул этап, он не отображается как успешно выполненный.

## 9. API client и запросы

API client разрабатывается в общем контуре вторым frontend-разработчиком.

Требования к использованию:

- все запросы выполняются через общий client;
- прямой fetch в компонентах не допускается;
- AbortSignal используется для отмены запросов;
- backend DTO преобразуется в доменный тип в API-модуле;
- retry применяется только к безопасным GET;
- mutation не повторяются автоматически без idempotency key;
- Error State получает нормализованный ApiError.

## 10. API Dashboard и Metrics

Базовый путь:

~~~text
/api/v1
~~~

### 10.1. Dashboard

~~~http
GET /dashboard?from=2026-09-25T00:00:00Z&to=2026-09-25T23:59:59Z&bucket=minute
~~~

Параметры:

| Параметр | Тип | Обязательный |
|---|---|---:|
| from | ISO date-time | нет |
| to | ISO date-time | нет |
| bucket | minute, hour, day | нет |

Ответ соответствует DashboardData.

Пример:

~~~json
{
  "summary": {
    "periodFrom": "2026-09-25T00:00:00Z",
    "periodTo": "2026-09-25T23:59:59Z",
    "generatedAt": "2026-09-25T17:42:12Z",
    "totalOrders": 1200,
    "assignedOrders": 1178,
    "unassignedOrders": 12,
    "failedOrders": 10,
    "activeExecutors": 41,
    "pendingAssignments": 18,
    "ordersPerSecond": 1.12,
    "averageAssignmentTimeMs": 48,
    "p95AssignmentTimeMs": 95,
    "ruleRejections": 340,
    "reservationConflicts": 14,
    "errors": 3
  },
  "timeline": [
    {
      "timestamp": "2026-09-25T17:41:00Z",
      "orders": 67,
      "assignments": 65,
      "failures": 2
    }
  ],
  "executorLoads": [
    {
      "executorId": 28,
      "executorName": "Петров И. В.",
      "capacityWeight": 1.5,
      "confirmedWeight": 4,
      "pendingWeight": 2,
      "effectiveLoad": 4,
      "dailyCount": 17,
      "maxDailyLimit": 40
    }
  ],
  "fairness": {
    "kind": "JAIN_INDEX",
    "value": 0.985,
    "target": 0.98,
    "description": "1.0 соответствует полностью равномерному распределению"
  },
  "latestAssignments": [
    {
      "orderId": 1032,
      "executorId": 28,
      "executorName": "Петров И. В.",
      "status": "assigned",
      "createdAt": "2026-09-25T17:42:10Z",
      "reservedAt": "2026-09-25T17:42:10Z",
      "confirmedAt": "2026-09-25T17:42:12Z",
      "processingTimeMs": 48,
      "explanation": "Выбран исполнитель с минимальной эффективной нагрузкой"
    }
  ]
}
~~~

### 10.2. Метрики

~~~http
GET /metrics?from=2026-09-25T00:00:00Z&to=2026-09-25T23:59:59Z&bucket=minute
~~~

Endpoint используется для расширенной аналитики или экспорта. Допускается совпадение части структуры с Dashboard.

Backend должен определить:

- формулу fairness;
- единицу ordersPerSecond;
- способ расчёта averageAssignmentTimeMs;
- способ расчёта p95AssignmentTimeMs;
- период агрегации;
- часовой пояс.

## 11. API Orders

Базовый путь:

~~~text
/api/v1/orders
~~~

### 11.1. Список заявок

~~~http
GET /orders?status=processed&assignmentStatus=assigned&vip=true&hasParent=false&search=1032&limit=20&offset=0
~~~

Параметры:

| Параметр | Тип | Обязательный |
|---|---|---:|
| status | OrderStatus | нет |
| assignmentStatus | AssignmentStatus | нет |
| orderType | string | нет |
| vip | boolean | нет |
| hasParent | boolean | нет |
| executorId | number | нет |
| search | string | нет |
| from | ISO date-time | нет |
| to | ISO date-time | нет |
| limit | number | нет |
| offset | number | нет |
| sort | string | нет |
| order | asc или desc | нет |

Ответ:

~~~json
{
  "items": [
    {
      "id": 1032,
      "parentId": null,
      "assignedExecutorId": 28,
      "sum": 300000,
      "clientMsp": "MSP_A",
      "executorMsp": "MSP_A",
      "orderType": "ORDER_1",
      "subject": "2f65db77-a08c-423c-a75d-bfc7af7ca788",
      "vip": true,
      "weight": 2,
      "text": "Срочная проверка договора",
      "status": "processed",
      "assignmentStatus": "assigned",
      "createdAt": "2026-09-25T17:42:10Z",
      "assignedAt": "2026-09-25T17:42:12Z",
      "processingTimeMs": 48
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 1200
  }
}
~~~

### 11.2. Одна заявка

~~~http
GET /orders/{id}
~~~

Ответ соответствует Order.

### 11.3. Список для Test Rule

~~~http
GET /orders/options?limit=50
~~~

Ответ:

~~~json
{
  "items": [
    {
      "id": 1032,
      "label": "#1032 — VIP — ORDER_1",
      "status": "processed",
      "vip": true
    }
  ]
}
~~~

Endpoint используется контуром второго frontend-разработчика и не должен требовать импорт компонентов Orders.

## 12. API Assignment и Decision Trace

### 12.1. Назначение по заявке

~~~http
GET /assignments/{orderId}
~~~

Ответ может содержать Assignment и DecisionTrace:

~~~json
{
  "assignment": {
    "orderId": 1032,
    "executorId": 28,
    "executorName": "Петров И. В.",
    "status": "assigned",
    "createdAt": "2026-09-25T17:42:10Z",
    "reservedAt": "2026-09-25T17:42:10Z",
    "confirmedAt": "2026-09-25T17:42:12Z",
    "processingTimeMs": 48,
    "explanation": "Выбран исполнитель с минимальной эффективной нагрузкой"
  },
  "decisionTrace": {
    "orderId": 1032,
    "timestamp": "2026-09-25T17:42:12Z",
    "processingTimeMs": 48,
    "modelVersion": "heuristic-v1",
    "rulesVersion": "rules-17",
    "totalExecutors": 50,
    "activeExecutors": 41,
    "eligibleExecutors": 8,
    "topKExecutors": 3,
    "selectedExecutorId": 28,
    "explanation": "Выбран наименее загруженный исполнитель из подходящих",
    "stages": [
      {
        "code": "TOTAL",
        "label": "Всего исполнителей",
        "inputCount": 50,
        "outputCount": 50,
        "durationMs": null
      },
      {
        "code": "ACTIVE",
        "label": "Активные исполнители",
        "inputCount": 50,
        "outputCount": 41,
        "durationMs": 2
      },
      {
        "code": "RULE_ENGINE",
        "label": "Rule Engine",
        "inputCount": 41,
        "outputCount": 8,
        "durationMs": 12
      },
      {
        "code": "RANKING",
        "label": "Ranking",
        "inputCount": 8,
        "outputCount": 3,
        "durationMs": 8
      },
      {
        "code": "RESERVATION",
        "label": "Atomic reservation",
        "inputCount": 3,
        "outputCount": 1,
        "durationMs": 4
      }
    ],
    "parentReuse": {
      "attempted": false,
      "parentOrderId": null,
      "previousExecutorId": null,
      "previousExecutorName": null,
      "previousExecutorActive": null,
      "parametersMatched": null,
      "dailyLimitIgnored": false,
      "reused": false,
      "reason": null
    },
    "candidates": [
      {
        "executorId": 28,
        "executorName": "Петров И. В.",
        "active": true,
        "passedRules": true,
        "failedRules": [],
        "dailyLimitReached": false,
        "rankScore": 0.91,
        "confirmedWeight": 4,
        "pendingWeight": 2,
        "effectiveLoad": 4,
        "reservationResult": "SUCCESS",
        "selected": true
      }
    ]
  }
}
~~~

### 12.2. Отсутствие назначения

При отсутствии подходящего кандидата:

- executorId = null;
- assignmentStatus = unassigned;
- explanation содержит причину;
- Decision Trace содержит этапы и причины исключения;
- candidates может содержать всех проверенных исполнителей.

### 12.3. Повторная заявка

Для parent_id должны возвращаться:

- parentOrderId;
- previousExecutorId;
- активность предыдущего исполнителя;
- соответствие обязательным параметрам;
- признак игнорирования суточного лимита;
- факт повторного назначения;
- причина перехода в обычный pipeline.

## 13. API-модули

### 13.1. Dashboard

~~~ts
export interface DashboardFilters {
  from?: string;
  to?: string;
  bucket?: 'minute' | 'hour' | 'day';
}

export function getDashboard(
  filters: DashboardFilters,
  signal?: AbortSignal,
): Promise<DashboardData>;

export function getMetrics(
  filters: DashboardFilters,
  signal?: AbortSignal,
): Promise<DashboardData>;
~~~

### 13.2. Orders

~~~ts
export interface OrderFilters {
  status?: OrderStatus;
  assignmentStatus?: AssignmentStatus;
  orderType?: string;
  vip?: boolean;
  hasParent?: boolean;
  executorId?: number;
  search?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export function getOrders(
  filters: OrderFilters,
  signal?: AbortSignal,
): Promise<PaginatedResponse<Order>>;

export function getOrder(
  id: number,
  signal?: AbortSignal,
): Promise<Order>;

export function getOrderOptions(
  signal?: AbortSignal,
): Promise<{ items: OrderOption[] }>;
~~~

### 13.3. Assignments

~~~ts
export interface AssignmentDetails {
  assignment: Assignment;
  decisionTrace: DecisionTrace;
}

export function getAssignmentByOrderId(
  orderId: number,
  signal?: AbortSignal,
): Promise<AssignmentDetails>;
~~~

## 14. Query keys и обновление данных

~~~ts
export const queryKeys = {
  dashboard: {
    all: ['dashboard'] as const,
    data: (filters: DashboardFilters) =>
      ['dashboard', filters] as const,
  },
  metrics: {
    all: ['metrics'] as const,
    data: (filters: DashboardFilters) =>
      ['metrics', filters] as const,
  },
  orders: {
    all: ['orders'] as const,
    list: (filters: OrderFilters) =>
      ['orders', 'list', filters] as const,
    detail: (id: number) =>
      ['orders', 'detail', id] as const,
    options: ['orders', 'options'] as const,
  },
  assignments: {
    detail: (orderId: number) =>
      ['assignments', orderId] as const,
  },
  executors: {
    all: ['executors'] as const,
  },
  rules: {
    all: ['rules'] as const,
  },
};
~~~

Режим обновления:

- Dashboard — polling 1.5–2 секунды;
- Orders — polling 2 секунды;
- Order Details — обновление по открытию и по фокусу;
- Decision Trace — запрос по открытию;
- завершённый Decision Trace может иметь длительный staleTime;
- pending/reserved назначение обновляется до финального состояния;
- polling останавливается при скрытой вкладке, если библиотека поддерживает это автоматически.

При изменении правила или исполнителя контур второго разработчика инвалидирует Dashboard.

## 15. Требования к Layout и навигации

Навигация должна содержать:

~~~text
Dashboard
Orders
Executors
Rules
~~~

Требования:

- активный раздел выделяется;
- навигация работает на 1366×768;
- заголовок страницы отображается;
- основные действия доступны без горизонтальной прокрутки;
- Sidebar не перекрывает содержимое;
- неизвестный маршрут показывает Not Found;
- ошибка одной страницы не разрушает Layout.

## 16. Требования к Dashboard

### 16.1. KPI

Обязательные карточки:

- всего заявок;
- назначено;
- не назначено;
- активные исполнители;
- среднее время назначения;
- p95 времени назначения.

Дополнительные:

- pending assignments;
- throughput;
- errors;
- reservation conflicts.

Каждая карточка должна содержать:

- название;
- значение;
- единицу;
- tooltip при неоднозначной метрике;
- состояние загрузки;
- отсутствие данных без отображения ложного нуля.

### 16.2. График динамики

Минимум один график:

- заявки по времени;
- назначения по времени;
- ошибки по времени.

Требования:

- ось времени;
- легенда;
- tooltip;
- корректная работа при одной точке;
- корректная работа при пустом массиве;
- отсутствие анимации, мешающей polling.

### 16.3. График нагрузки

Для каждого исполнителя:

- confirmedWeight;
- pendingWeight;
- effectiveLoad;
- capacityWeight в tooltip.

Confirmed и pending должны визуально различаться и иметь подписи.

### 16.4. Fairness

Отображение должно содержать:

- тип метрики;
- значение;
- целевое значение;
- описание;
- период расчёта.

Jain Index не должен подписываться как процент отклонения.

### 16.5. Последние назначения

Таблица:

| Колонка | Содержание |
|---|---|
| Время | createdAt или confirmedAt |
| Заявка | orderId |
| Исполнитель | executorName |
| Статус | AssignmentStatus |
| Время решения | processingTimeMs |
| Действие | открыть Decision Trace |

### 16.6. Состояния

- Loading — skeleton;
- Error — сообщение и Retry;
- Empty — отсутствие данных за период;
- Success;
- Stale — время последнего успешного обновления;
- Background fetching — ненавязчивый индикатор.

## 17. Требования к Orders

### 17.1. Фильтры

- поиск по ID;
- status;
- assignmentStatus;
- orderType;
- VIP;
- parent_id;
- период;
- исполнитель при наличии времени.

Фильтры должны храниться в состоянии страницы. Синхронизация с URL относится к P1.

### 17.2. Таблица

| Колонка | Содержание |
|---|---|
| ID | orderId |
| Создана | createdAt |
| Тип | orderType |
| VIP | признак |
| Вес | weight |
| Статус заявки | OrderStatus |
| Статус назначения | AssignmentStatus |
| Исполнитель | имя или «Не назначен» |
| Время решения | processingTimeMs |
| Повторная | parentId |
| Действие | детали |

### 17.3. Поведение

- строка открывает Order Details;
- фильтры не должны блокировать polling;
- обновление не должно сбрасывать выбранную страницу без необходимости;
- новые данные не должны неожиданно закрывать Drawer;
- null отображается явно;
- длинный текст не растягивает таблицу.

### 17.4. Состояния

- Loading;
- Error с Retry;
- Empty;
- Success;
- Background refresh.

## 18. Требования к Order Details

Должны отображаться:

- ID;
- parent_id;
- статус заявки;
- статус назначения;
- тип;
- сумма;
- VIP;
- subject;
- clientMsp;
- executorMsp;
- вес;
- текст;
- дата создания;
- дата назначения;
- время решения;
- назначенный исполнитель;
- объяснение результата.

Должна быть доступна команда открытия Decision Trace.

Для повторной заявки должна быть ссылка или действие перехода к родительской заявке.

## 19. Требования к Decision Trace

### 19.1. Назначение

Экран должен отвечать на вопрос:

~~~text
Почему заявка была назначена этому исполнителю
или почему назначение не состоялось
~~~

### 19.2. Этапы

Отображаются только этапы, возвращённые backend:

~~~text
Всего исполнителей
→ Активные
→ Rule Engine
→ Ranking
→ Balancing
→ Reservation
→ Assignment
~~~

Для этапа отображаются:

- название;
- количество на входе;
- количество на выходе;
- длительность при наличии.

### 19.3. Кандидаты

Таблица:

| Колонка | Содержание |
|---|---|
| Исполнитель | executorName |
| Активен | active |
| Rule Engine | passedRules |
| Причины отказа | failedRules |
| Daily limit | dailyLimitReached |
| Rank score | rankScore |
| Confirmed | confirmedWeight |
| Pending | pendingWeight |
| Effective load | effectiveLoad |
| Reservation | reservationResult |
| Выбран | selected |

Должны поддерживаться:

- фильтр «все / прошедшие / исключённые»;
- раскрытие причин;
- выделение выбранного кандидата;
- отсутствие rankScore;
- несколько failedRules;
- отсутствие выбранного исполнителя.

### 19.4. Parent reuse

Отдельный блок должен показывать:

- была ли попытка возврата;
- parentOrderId;
- предыдущего исполнителя;
- его активность;
- соответствие параметрам;
- игнорирование суточного лимита;
- итог повторного назначения;
- причину стандартного распределения.

### 19.5. Объяснение

Backend explanation отображается как основной текст.

Frontend может форматировать структурированные данные, но не должен генерировать неподтверждённую причину.

### 19.6. Состояния

- Loading;
- Error;
- Trace unavailable;
- Assignment pending;
- Assignment completed;
- No eligible executors.

## 20. Требования к экспорту

Экспорт относится к P1 и реализуется после стабильного P0.

Поддерживаемые форматы:

- XLSX;
- CSV как резервный вариант.

XLSX должен содержать листы:

1. Summary;
2. Assignments;
3. Executor Load.

Summary:

- период;
- время формирования;
- KPI;
- fairness;
- тип fairness.

Assignments:

- orderId;
- executorId;
- executorName;
- status;
- processingTimeMs;
- createdAt;
- confirmedAt.

Executor Load:

- executorId;
- executorName;
- capacityWeight;
- confirmedWeight;
- pendingWeight;
- effectiveLoad;
- dailyCount;
- maxDailyLimit.

Имя файла:

~~~text
executor-balancer-report-YYYY-MM-DD-HHmm.xlsx
~~~

Экспорт должен использовать отображаемый период и не должен блокировать Dashboard.

## 21. Требования к мокам

Файлы:

~~~text
src/mocks/dashboard.ts
src/mocks/orders.ts
src/mocks/assignments.ts
~~~

Моки должны:

- возвращать Promise;
- имитировать задержку 200–500 мс;
- соответствовать API DTO;
- поддерживать явные ошибки;
- не импортироваться UI-компонентами;
- содержать стабильный demo dataset;
- изменять временные метрики для имитации потока при необходимости.

Сценарии Dashboard:

1. нормальная нагрузка;
2. pending assignments;
3. reservation conflicts;
4. высокий throughput;
5. пустой период;
6. ошибка API.

Сценарии Orders:

1. обычная назначенная заявка;
2. VIP;
3. parent_id;
4. unassigned;
5. failed;
6. pending;
7. длинный текст;
8. null сумма;
9. пустой список.

Сценарии Decision Trace:

1. успешное назначение;
2. кандидаты исключены правилами;
3. достигнут суточный лимит;
4. reservation conflict и переход к следующему кандидату;
5. нет подходящих кандидатов;
6. parent reuse успешен;
7. parent reuse не выполнен;
8. ranking отсутствует;
9. trace недоступен;
10. assignment ещё pending.

## 22. Компоненты

Предлагаемый состав:

~~~text
AppLayout
Sidebar
Header
StatusBadge

DashboardPage
KpiCard
OrdersTimelineChart
ExecutorLoadChart
FairnessIndicator
LatestAssignmentsTable
DataFreshnessIndicator

OrdersPage
OrderFilters
OrdersTable
OrderDetailsDrawer

DecisionTraceView
DecisionStages
DecisionStageItem
ParentReusePanel
CandidateTable
FailedRulesList
AssignmentExplanation

ExportReportButton
~~~

Базовые UI-примитивы должны использоваться из общего UI-kit.

## 23. Интеграция с контуром второго frontend-разработчика

### 23.1. Общие данные

- ExecutorSummary используется Dashboard и Decision Trace;
- OrderOption используется Test Rule;
- Rule ID и Rule Name отображаются в failedRules;
- изменение Rule инвалидирует Dashboard;
- изменение Executor инвалидирует Dashboard;
- StatusBadge является общим;
- query keys фиксируются совместно.

### 23.2. Запрещённые зависимости

- Dashboard не импортирует компоненты Rules;
- Decision Trace не импортирует Rule Constructor;
- Orders не импортирует компоненты Executors;
- shared/types не импортирует features;
- API-модули не импортируют React;
- компоненты не вызывают fetch напрямую;
- доменные типы не дублируются.

### 23.3. Согласования первого дня

- ExecutorSummary;
- Rule ID и Rule Name;
- FailedRule;
- OrderOption;
- ApiError;
- query keys;
- base URL;
- polling interval;
- mock/API switch;
- словарь статусов;
- формат дат;
- формат fairness.

## 24. Нефункциональные требования

- корректная работа на 1366×768 и 1920×1080;
- отсутствие горизонтального переполнения основных экранов;
- отсутствие ошибок console;
- клавиатурная доступность основных действий;
- видимый focus;
- цвет не является единственным индикатором;
- графики имеют легенду и tooltip;
- polling не создаёт мерцание;
- предыдущие данные сохраняются при background refresh;
- устаревшие запросы отменяются;
- null не вызывает падение;
- время отображается в согласованном часовом поясе;
- формат чисел и длительности единообразен;
- бизнес-метрики не вычисляются как источник истины;
- интерфейс показывает время последнего успешного обновления.

## 25. План выполнения

## День 1

Общие работы:

- фиксация DTO;
- фиксация ApiError;
- фиксация Decision Trace;
- фиксация fairness;
- распределение общих файлов;
- фиксация demo flow.

Работы контура:

- router;
- Layout;
- Sidebar;
- Header;
- StatusBadge;
- типы Order, Assignment, Dashboard и Decision Trace;
- доменные моки;
- таблица Orders;
- каркас Dashboard;
- переход к пустому Decision Trace.

Результат:

- маршруты работают;
- Orders отображается на моках;
- Dashboard отображает каркас;
- Decision Trace открывается;
- UI не импортирует моки напрямую.

## День 2

- полноценный Decision Trace;
- этапы фильтрации;
- таблица кандидатов;
- failedRules;
- confirmed, pending и effectiveLoad;
- parent_id;
- KPI Dashboard;
- timeline;
- график нагрузки;
- последние назначения.

Результат:

~~~text
Dashboard
→ Orders
→ Order Details
→ Decision Trace
→ объяснение выбора
~~~

Сценарий должен работать на моках.

## День 3

- подключение Dashboard API;
- подключение Metrics API;
- подключение Orders API;
- подключение Assignments API;
- polling;
- Loading, Error и Empty;
- pending → assigned;
- parent reuse;
- проверка обновления после Rules и Executors mutation;
- экспорт после готовности P0.

Результат:

- основной сценарий работает с backend;
- mock-режим запускается отдельно;
- сетевые ошибки отображаются;
- Dashboard не теряет предыдущие данные при refresh.

## День 4

- устранение блокирующих дефектов;
- проверка 1366×768 и 1920×1080;
- проверка длинных значений;
- проверка пустых данных;
- проверка ошибок;
- burst-сценарий;
- VIP-сценарий;
- parent_id-сценарий;
- reservation conflict;
- экспорт при готовности;
- общая репетиция.

Добавление новых крупных функций в день 4 не допускается.

## 26. Приоритеты

### P0

- Layout и маршруты;
- Dashboard KPI;
- один timeline;
- confirmed/pending load;
- Orders;
- Order Details;
- Decision Trace;
- failedRules;
- parent_id;
- Loading, Error и Empty;
- polling;
- mock/API;
- стабильный demo flow.

### P1

- fairness;
- p95;
- reservation conflicts;
- Excel/CSV;
- расширенные графики;
- фильтр кандидатов;
- URL-фильтры Orders.

### P2

- SSE/WebSocket;
- сложные анимации;
- сохранённые отчёты;
- дополнительные темы;
- конструктор отчётов;
- расширенная ML-аналитика.

При дефиците времени функции исключаются в следующем порядке:

1. дополнительные графики;
2. URL-фильтры;
3. Excel;
4. фильтр кандидатов;
5. fairness-визуализация при сохранении сырой метрики;
6. p95-карточка при отсутствии backend-метрики.

Decision Trace, Orders и базовый Dashboard сохраняются обязательно.

## 27. Критерии приёмки

### 27.1. Layout

- все основные маршруты доступны;
- активный раздел выделяется;
- неизвестный маршрут обрабатывается;
- 1366×768 поддерживается;
- навигация не перекрывает содержимое.

### 27.2. Dashboard

- KPI загружаются через API-модуль;
- минимум один график работает;
- confirmed и pending отображаются раздельно;
- последние назначения открывают Decision Trace;
- тип fairness подписан корректно;
- время последнего обновления отображается;
- Loading, Error и Empty реализованы;
- polling не вызывает мерцание.

### 27.3. Orders

- список загружается;
- фильтры работают;
- статусы заявки и назначения разделены;
- parent_id отображается;
- строка открывает детали;
- Loading, Error и Empty реализованы;
- обновление не закрывает детали.

### 27.4. Order Details

- параметры заявки отображаются;
- назначенный исполнитель отображается;
- null обрабатывается;
- родительская заявка доступна;
- Decision Trace открывается.

### 27.5. Decision Trace

- этапы отображаются из backend DTO;
- причины исключения отображаются;
- rankScore допускает null;
- confirmed, pending и effectiveLoad отображаются;
- reservationResult отображается;
- выбранный кандидат выделяется;
- отсутствие кандидата обрабатывается;
- parent reuse отображается;
- backend explanation присутствует;
- недоступность trace имеет отдельное состояние.

### 27.6. Общая инфраструктура

- mock и API используют одинаковые DTO;
- прямой fetch отсутствует;
- типы не дублируются;
- query keys согласованы;
- необработанные ошибки console отсутствуют;
- данные не подменяются моками автоматически.

## 28. Проверки перед интеграцией

- [ ] Backend подтвердил OrderStatus.
- [ ] Backend подтвердил AssignmentStatus.
- [ ] Backend подтвердил DashboardData.
- [ ] Backend подтвердил формулу fairness.
- [ ] Backend подтвердил единицы throughput.
- [ ] Backend подтвердил avg и p95.
- [ ] Backend подтвердил DecisionTrace.
- [ ] Backend возвращает ruleId и ruleName.
- [ ] Backend возвращает confirmed и pending.
- [ ] Backend возвращает reservationResult.
- [ ] Backend возвращает parentReuse.
- [ ] Контур второго разработчика использует OrderOption.
- [ ] Оба контура используют общий ExecutorSummary.
- [ ] ApiError согласован.
- [ ] Mock/API switch проверен.
- [ ] Query keys согласованы.
- [ ] Polling interval согласован.

## 29. Демонстрационный сценарий

1. После создания правила в Rules запускается поток заявок.
2. Dashboard отображает рост числа заявок.
3. Отображаются throughput, назначения и pending.
4. График нагрузки показывает confirmed и pending.
5. Fairness отображается с точным названием метрики.
6. В Orders выбирается новая VIP-заявка.
7. Order Details показывает параметры и назначенного исполнителя.
8. Decision Trace показывает этапы фильтрации.
9. Отображаются правила, исключившие кандидатов.
10. Отображаются rankScore и effectiveLoad.
11. Отображается reservationResult.
12. Отображается выбранный исполнитель.
13. Для повторной заявки демонстрируется parent reuse.
14. При готовности формируется XLSX или CSV.

## 30. Проектная документация

В общий комплект сдачи должны входить:

- BPMN-диаграмма;
- sequence-диаграмма;
- ERD;
- описание ключевых проблем;
- описание альтернативных решений.

Вклад frontend-контура мониторинга:

- пользовательский сценарий Dashboard → Orders → Decision Trace;
- frontend-участник sequence-диаграммы;
- polling запросы;
- DTO Order, Assignment, Dashboard и Decision Trace;
- описание состояний pending, reserved и assigned;
- описание отображения parent_id;
- описание визуализации fairness.

Владение полным комплектом диаграмм должно быть назначено в общей команде до конца первого дня.

## 31. Результат работ

Завершённый frontend-контур должен обеспечивать следующий процесс:

~~~text
Поступление заявок
→ обновление Dashboard
→ просмотр списка Orders
→ открытие конкретной заявки
→ просмотр Decision Trace
→ объяснение правил, нагрузки и резервирования
→ отображение выбранного исполнителя
~~~

Ключевой результат — возможность наглядно доказать корректность, прозрачность и справедливость распределения заявок на основании данных backend.
