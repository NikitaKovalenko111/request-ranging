package config

type Config struct {
	App         AppConfig
	HTTP        HTTPConfig
	Postgres    PostgresConfig
	Redis       RedisConfig
	Kafka       KafkaConfig
	AIS         AISConfig
	Reservation ReservationConfig
}

func Load() (Config, error) {
	app, err := loadAppConfig()
	if err != nil {
		return Config{}, err
	}
	httpConfig, err := loadHTTPConfig()
	if err != nil {
		return Config{}, err
	}
	postgres, err := loadPostgresConfig()
	if err != nil {
		return Config{}, err
	}
	redis, err := loadRedisConfig()
	if err != nil {
		return Config{}, err
	}
	kafka, err := loadKafkaConfig()
	if err != nil {
		return Config{}, err
	}
	ais, err := loadAISConfig()
	if err != nil {
		return Config{}, err
	}
	reservation, err := loadReservationConfig()
	if err != nil {
		return Config{}, err
	}

	return Config{
		App:         app,
		HTTP:        httpConfig,
		Postgres:    postgres,
		Redis:       redis,
		Kafka:       kafka,
		AIS:         ais,
		Reservation: reservation,
	}, nil
}
