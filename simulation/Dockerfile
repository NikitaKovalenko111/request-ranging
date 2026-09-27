FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt aiosqlite

COPY . .

ENV APP_HTTP_ADDR=:8091
ENV KAFKA_BROKERS=kafka:9092
ENV KAFKA_ENABLED=true
ENV ORDER_TOPIC=ais.orders.v1
ENV EXECUTOR_TOPIC=ais.executors.v1
ENV ASSIGNMENT_DELAY_MIN=2s
ENV ASSIGNMENT_DELAY_MAX=10s
ENV DATABASE_URL=sqlite+aiosqlite:///./ais.db

EXPOSE 8091

CMD ["python", "run.py"]
