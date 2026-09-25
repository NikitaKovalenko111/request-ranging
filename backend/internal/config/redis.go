package config

type RedisConfig struct {
	Address string
}

func loadRedisConfig() (RedisConfig, error) {
	config := RedisConfig{Address: envOrDefault("REDIS_ADDR", "localhost:6379")}
	if err := validateHostPort("REDIS_ADDR", config.Address); err != nil {
		return RedisConfig{}, err
	}
	return config, nil
}
