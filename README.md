# Executor Balancer Frontend

Frontend-контур мониторинга и объяснимости распределения заявок. Проект реализован на Vite, React и TypeScript и по умолчанию работает на стабильных доменных моках.

## Запуск

```bash
npm install
npm run dev
```

Проверка типов и production-сборка:

```bash
npm run typecheck
npm run build
```

## Источник данных

Скопируйте `.env.example` в `.env.local`. Значение `VITE_DATA_SOURCE=mock` включает демонстрационные данные, `VITE_DATA_SOURCE=api` — реальные endpoints backend. При ошибке API автоматического переключения на моки нет.

Основные маршруты:

- `/dashboard` — метрики, графики нагрузки и последние назначения;
- `/orders` — список и фильтры заявок;
- `/orders/:id` — заявка, назначение и Decision Trace;
- `/executors` и `/rules` — точки интеграции соседнего frontend-контура.

Подробный план находится в `Docs/IMPLEMENTATION_PLAN.md`, назначение файлов — в `Docs/PROJECT_FILES.md`.
