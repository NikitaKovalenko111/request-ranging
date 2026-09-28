# Executor Balancer

Единый локальный контур из трёх сервисов:

    AIS Simulator
      -> ais.executors.v1 / ais.orders.v1
    Backend
      -> PostgreSQL + Redis profiles/runtime load
    Decision Engine
      -> Rule Engine -> Feature Extractor -> ML Ranker -> Balancer
      -> decision.result.v1
    Backend
      -> atomic reservation -> POST /api/v1/assignments
    AIS Simulator

## Запуск

Требуется запущенный Docker Desktop.

    docker compose up --build -d
    docker compose ps

Адреса:

- AIS Simulator: http://localhost:8091/docs
- Backend health: http://localhost:8090/health
- Backend readiness: http://localhost:8090/ready
- Kafka: localhost:9092
- Redis: localhost:6380
- PostgreSQL: localhost:5442

После первого запуска AIS автоматически создаёт исполнителей и публикует полный
snapshot в Kafka. Генерация заявок запускается отдельно:

    Invoke-RestMethod -Method Post -Uri http://localhost:8091/api/v1/simulation/start -ContentType application/json -Body '{"mode":"slow","target_orders":20,"orders_per_hour":3600,"start_lifecycle":false}'

Для сквозной smoke-проверки одной заявки:

    scripts/e2e-smoke.ps1

Lifecycle можно включить после проверки назначения. Остановка:

    docker compose down

Полностью чистый повторный запуск:

    docker compose down -v
    docker compose up --build -d

## Единые контракты

| Назначение | Значение |
|---|---|
| заявки AIS | ais.orders.v1 |
| исполнители AIS | ais.executors.v1 |
| решения Decision Engine | decision.result.v1 |
| активные исполнители Redis | executors:active |
| профиль и нагрузка | executor:{executor_id} Redis Hash |
| ID заявки/исполнителя | string |

Decision Engine использует обученный ranker-v2, если артефакты модели доступны,
и автоматически переходит на heuristic ranker при невозможности загрузки модели.
Для отсутствующих исторических ML-признаков применяются cold-start значения,
пока реальные агрегаты не появятся в AIS/backend.

## Проверки без Docker

    cd backend
    go test ./...
    go vet ./...

    cd ../decision-engine
    .venv/Scripts/python.exe -m pytest
