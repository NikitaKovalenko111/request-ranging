import os
import re
from pydantic import BaseModel, Field


def parse_duration_to_seconds(value: str | float | int, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    val_str = str(value).strip().lower()
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)(ms|s|m|h)?$", val_str)
    if not match:
        try:
            return float(val_str)
        except ValueError:
            return default
    num, unit = match.groups()
    num = float(num)
    if unit == "ms":
        return num / 1000.0
    elif unit == "m":
        return num * 60.0
    elif unit == "h":
        return num * 3600.0
    else:  # 's' or None
        return num


class Settings(BaseModel):
    app_http_addr: str = Field(default_factory=lambda: os.getenv("APP_HTTP_ADDR", ":8091"))
    host: str = "0.0.0.0"
    port: int = 8091
    
    kafka_brokers: str = Field(default_factory=lambda: os.getenv("KAFKA_BROKERS", "localhost:9092"))
    kafka_enabled: bool = Field(default_factory=lambda: os.getenv("KAFKA_ENABLED", "false").lower() in ("true", "1", "yes"))
    
    order_topic: str = Field(default_factory=lambda: os.getenv("ORDER_TOPIC", "ais.orders.v1"))
    executor_topic: str = Field(default_factory=lambda: os.getenv("EXECUTOR_TOPIC", "ais.executors.v1"))
    
    assignment_delay_min: float = 2.0
    assignment_delay_max: float = 10.0

    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ais.db"))

    # Настройки скорости потока и пиковых нагрузок
    orders_per_hour: float = Field(default_factory=lambda: float(os.getenv("ORDERS_PER_HOUR", "4000.0")))
    max_peak_per_sec: int = Field(default_factory=lambda: int(os.getenv("MAX_PEAK_PER_SEC", "5")))

    @classmethod
    def load(cls) -> "Settings":
        addr = os.getenv("APP_HTTP_ADDR", ":8091")
        host = "0.0.0.0"
        port = 8091
        if ":" in addr:
            parts = addr.split(":")
            if parts[0]:
                host = parts[0]
            if parts[1]:
                port = int(parts[1])
        elif addr.isdigit():
            port = int(addr)

        delay_min_raw = os.getenv("ASSIGNMENT_DELAY_MIN", "2s")
        delay_max_raw = os.getenv("ASSIGNMENT_DELAY_MAX", "10s")
        delay_min = parse_duration_to_seconds(delay_min_raw, 2.0)
        delay_max = parse_duration_to_seconds(delay_max_raw, 10.0)
        if delay_max < delay_min:
            delay_max = delay_min

        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ais.db")

        return cls(
            app_http_addr=addr,
            host=host,
            port=port,
            assignment_delay_min=delay_min,
            assignment_delay_max=delay_max,
            database_url=db_url,
        )


settings = Settings.load()
