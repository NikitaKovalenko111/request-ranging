# Документация структуры frontend проекта

Этот файл объясняет назначение файлов проекта и должен обновляться при изменении структуры. Он специально хранится в Git и не входит в `.gitignore`.

## Корень проекта

| Файл | Назначение |
|---|---|
| `.env.example` | Пример настроек источника данных, URL backend и интервала polling. |
| `.gitignore` | Исключает зависимости, сборку, локальные секреты, логи и временные файлы. |
| `index.html` | HTML-точка входа Vite и контейнер React-приложения. |
| `package.json` | Зависимости и команды разработки, проверки типов и сборки. |
| `package-lock.json` | Зафиксированные версии npm-зависимостей для воспроизводимой установки. |
| `tsconfig.json` | Строгие настройки TypeScript для исходного кода. |
| `tsconfig.node.json` | Настройки TypeScript для конфигурации Vite. |
| `vite.config.ts` | Конфигурация Vite и React-плагина. |
| `README.md` | Краткая инструкция по установке, запуску и режимам данных. |

## Документация

| Файл | Назначение |
|---|---|
| `Docs/IMPLEMENTATION_PLAN.md` | Мелкий пошаговый план разработки с отметками выполнения. |
| `Docs/PROJECT_FILES.md` | Карта файлов и ответственности модулей проекта. |
| `Docs/FRONTEND_DEVELOPER_1_TECHNICAL_SPECIFICATION.md` | Подробное техническое задание frontend-контура. |
| `Docs/EXECUTOR_BALANCER_FUNCTIONS.md` | Описание функций всей системы Executor Balancer. |
| `Docs/Кейс_хакатон_2026.docx` | Исходное описание хакатон-кейса. |

## Приложение и маршрутизация

| Файл | Назначение |
|---|---|
| `src/main.tsx` | Монтирует React-приложение и подключает глобальные стили. |
| `src/app/App.tsx` | Корневой компонент приложения. |
| `src/app/providers.tsx` | Подключает QueryClient и BrowserRouter. |
| `src/app/queryClient.ts` | Единая конфигурация кэша, retry и времени актуальности запросов. |
| `src/app/router.tsx` | Описывает все маршруты и связывает страницы с Layout. |

## API слой

| Файл | Назначение |
|---|---|
| `src/api/client.ts` | Выполняет HTTP GET, нормализует ошибки и поддерживает AbortSignal. |
| `src/api/dataSource.ts` | Выбирает mock или реальный API строго по переменной окружения. |
| `src/api/dashboard.ts` | Загружает Dashboard и формирует CSV-отчёт из отображаемых данных. |
| `src/api/orders.ts` | Загружает список заявок и отдельную заявку. |
| `src/api/assignments.ts` | Загружает назначение и Decision Trace заявки. |

## Доменные типы

| Файл | Назначение |
|---|---|
| `src/types/api.ts` | Общие API-ошибки и типы пагинации. |
| `src/types/order.ts` | Статусы и поля заявки, фильтры списка. |
| `src/types/assignment.ts` | Назначение и статусы назначения. |
| `src/types/dashboard.ts` | KPI, временные ряды, нагрузка и fairness. |
| `src/types/decisionTrace.ts` | Этапы решения, кандидаты и parent reuse. |

## Моки

| Файл | Назначение |
|---|---|
| `src/mocks/orders.ts` | Стабильный набор заявок с VIP, parent, pending, failed и null-сценариями. |
| `src/mocks/assignments.ts` | Назначения и трассы решений для демонстрационных заявок. |
| `src/mocks/dashboard.ts` | KPI, динамика потока, нагрузки исполнителей и последние назначения. |
| `src/mocks/utils.ts` | Имитирует сетевую задержку и поддерживает отмену запроса. |

## Общие модули

| Файл | Назначение |
|---|---|
| `src/shared/config/env.ts` | Валидирует и экспортирует runtime-настройки приложения. |
| `src/shared/config/queryKeys.ts` | Централизованные ключи TanStack Query. |
| `src/shared/format/index.ts` | Единое форматирование дат, длительности, чисел, денег и процентов. |
| `src/shared/components/AppLayout.tsx` | Адаптивная оболочка страницы с навигацией и заголовком. |
| `src/shared/components/StatusBadge.tsx` | Унифицированное текстовое и цветовое отображение статусов. |
| `src/shared/components/StateViews.tsx` | Loading, Error и Empty состояния. |
| `src/shared/components/DataFreshness.tsx` | Время обновления и индикатор фонового запроса. |
| `src/shared/components/MetricTooltip.tsx` | Доступная подсказка к неоднозначным метрикам. |

## Dashboard

| Файл | Назначение |
|---|---|
| `src/features/dashboard/hooks/useDashboard.ts` | Получает Dashboard через TanStack Query и polling. |
| `src/features/dashboard/components/KpiCard.tsx` | Карточка одной KPI с единицей и пояснением. |
| `src/features/dashboard/components/OrdersTimelineChart.tsx` | График заявок, назначений и ошибок по времени. |
| `src/features/dashboard/components/ExecutorLoadChart.tsx` | График confirmed и pending нагрузки исполнителей. |
| `src/features/dashboard/components/FairnessCard.tsx` | Точное представление fairness и целевого значения. |
| `src/features/dashboard/components/LatestAssignmentsTable.tsx` | Таблица последних назначений с переходом к деталям. |
| `src/features/dashboard/pages/DashboardPage.tsx` | Собирает полный экран Dashboard и экспорт отчёта. |

## Заявки и Decision Trace

| Файл | Назначение |
|---|---|
| `src/features/orders/hooks/useOrders.ts` | Получает список и детали заявок с polling. |
| `src/features/orders/components/OrderFilters.tsx` | Управляет фильтрами списка заявок. |
| `src/features/orders/components/OrdersTable.tsx` | Адаптивная таблица заявок и переход к деталям. |
| `src/features/orders/pages/OrdersPage.tsx` | Экран списка заявок со всеми состояниями. |
| `src/features/orders/pages/OrderDetailsPage.tsx` | Полная карточка заявки, назначение и Decision Trace. |
| `src/features/decision-trace/hooks/useDecisionTrace.ts` | Загружает назначение и трассу решения. |
| `src/features/decision-trace/components/DecisionTraceView.tsx` | Визуализирует этапы, parent reuse и кандидатов. |

## Служебные страницы и стили

| Файл | Назначение |
|---|---|
| `src/features/placeholders/PlaceholderPage.tsx` | Честно обозначает маршруты соседнего frontend-контура. |
| `src/features/not-found/NotFoundPage.tsx` | Обрабатывает неизвестный маршрут. |
| `src/styles.css` | Общая визуальная система, layout, таблицы, графики и адаптивность. |
