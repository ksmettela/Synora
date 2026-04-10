package config

import (
	"fmt"

	"github.com/caarlos0/env/v10"
)

// Config holds all application configuration
type Config struct {
	ListenAddr            string `env:"LISTEN_ADDR" envDefault:":8080"`
	KafkaBootstrapServers string `env:"KAFKA_BOOTSTRAP_SERVERS" envDefault:"localhost:9092"`
	KafkaTopic            string `env:"KAFKA_TOPIC" envDefault:"raw.fingerprints"`
	RedisURL              string `env:"REDIS_URL" envDefault:"redis://localhost:6379"`
	MaxMindDBPath         string `env:"MAXMIND_DB_PATH" envDefault:"/etc/geoip/GeoLite2-ASN.mmdb"`
	RateLimitPerSecond    int    `env:"RATE_LIMIT_PER_SECOND" envDefault:"10000"`
	MaxBatchSize          int    `env:"MAX_BATCH_SIZE" envDefault:"100"`
	TimestampToleranceSec int    `env:"TIMESTAMP_TOLERANCE_SEC" envDefault:"300"`
	MetricsListenAddr     string `env:"METRICS_LISTEN_ADDR" envDefault:":9090"`
}

// Load loads configuration from environment variables
func Load() (*Config, error) {
	cfg := &Config{}
	if err := env.Parse(cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}
	return cfg, nil
}
