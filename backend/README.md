# Executor Balancer

Основной backend сервис распределения заявок между исполнителями.

## Требования

- Go 1.25 или новее;
- Docker Desktop для локальной инфраструктуры.

## Запуск инфраструктуры

Из каталога `backend`:

```text
docker compose up -d
```

При первом создании PostgreSQL volume файл `migrations/001_initial.up.sql` применяется автоматически. Если volume уже существовал до добавления миграции, примените её вручную из PowerShell:

```text
Get-Content -Raw .\migrations\001_initial.up.sql |
    docker compose exec -T postgres psql -U executor_balancer -d executor_balancer
```

Миграции создают таблицы заявок, исполнителей, правил, назначений, истории решений и обработанных Kafka событий. После обновления существующего окружения примените новые миграции `002_executor_skills.up.sql` и `003_assignment_integrity.up.sql` вручную, если PostgreSQL volume уже был создан.

## Локальный запуск приложения

После запуска инфраструктуры:

```text
go run ./cmd/balancer
```

По умолчанию сервис доступен на `http://localhost:8090`.

## Проверки состояния

```text
GET /health
GET /ready
```

`/health` подтверждает, что HTTP процесс работает.

`/ready` проверяет TCP доступность PostgreSQL, Redis и всех Kafka brokers. Если хотя бы одна зависимость недоступна, endpoint возвращает `503 Service Unavailable`.

## Проверка кода

```text
go test ./...
go vet ./...
```

## Конфигурация

Список переменных окружения находится в `.env.example`. Приложение не загружает `.env` автоматически: переменные должны быть переданы через оболочку, IDE или Docker Compose.
