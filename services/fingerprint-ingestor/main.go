package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-redis/redis/v9"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/valyala/fasthttp"
	"go.uber.org/zap"

	"github.com/synora/acraas/services/fingerprint-ingestor/config"
	"github.com/synora/acraas/services/fingerprint-ingestor/geoip"
	"github.com/synora/acraas/services/fingerprint-ingestor/handler"
	"github.com/synora/acraas/services/fingerprint-ingestor/kafka"
	"github.com/synora/acraas/services/fingerprint-ingestor/middleware"
	"github.com/synora/acraas/services/fingerprint-ingestor/ratelimit"
)

func main() {
	// Initialize logger
	logger, err := zap.NewProduction()
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to create logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		logger.Fatal("failed to load config", zap.Error(err))
	}

	logger.Info("fingerprint-ingestor starting",
		zap.String("listen_addr", cfg.ListenAddr),
		zap.String("kafka_bootstrap", cfg.KafkaBootstrapServers),
		zap.String("metrics_addr", cfg.MetricsListenAddr),
	)

	// Initialize Redis client
	redisClient := redis.NewClient(&redis.Options{
		Addr: cfg.RedisURL,
	})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := redisClient.Ping(ctx).Err(); err != nil {
		logger.Fatal("redis connection failed", zap.Error(err))
	}
	defer redisClient.Close()

	// Initialize Kafka producer
	kafkaProducer, err := kafka.NewProducer(cfg.KafkaBootstrapServers, cfg.KafkaTopic, logger)
	if err != nil {
		logger.Fatal("failed to create kafka producer", zap.Error(err))
	}
	defer kafkaProducer.Close()

	// Initialize GeoIP filter
	geoIPFilter, err := geoip.NewFilter(cfg.MaxMindDBPath, logger)
	if err != nil {
		logger.Warn("failed to initialize geoip filter", zap.Error(err))
	}
	defer geoIPFilter.Close()

	// Initialize rate limiter
	rateLimiter := ratelimit.NewLimiter(redisClient, cfg.RateLimitPerSecond)

	// Initialize middleware and handlers
	authMiddleware := middleware.NewAuth(redisClient, logger)
	ingestHandler := handler.NewIngestHandler(kafkaProducer, rateLimiter, geoIPFilter, logger, cfg.MaxBatchSize, cfg.TimestampToleranceSec)
	healthHandler := handler.NewHealthHandler(redisClient, logger)

	// Set up routes
	router := fasthttp.RequestHandler(func(ctx *fasthttp.RequestCtx) {
		switch string(ctx.Path()) {
		case "/health":
			if ctx.IsGet() {
				healthHandler.Health(ctx)
			} else {
				ctx.SetStatusCode(fasthttp.StatusMethodNotAllowed)
			}

		case "/metrics":
			// Prometheus metrics endpoint
			handler.MetricsHandler(ctx)

		case "/v1/fingerprints":
			if ctx.IsPost() {
				authMiddleware.Middleware(ingestHandler.Handle)(ctx)
			} else {
				ctx.SetStatusCode(fasthttp.StatusMethodNotAllowed)
			}

		default:
			ctx.SetStatusCode(fasthttp.StatusNotFound)
			fmt.Fprintf(ctx, `{"error":"not found"}`)
		}
	})

	// Start HTTP server
	httpServer := &fasthttp.Server{
		Handler:     router,
		ReadTimeout: 10 * time.Second,
		MaxConns:    100000,
		Concurrency: 1000000,
		Logger:      &fastHTTPLogger{logger},
	}

	// Start metrics server (separate port)
	go func() {
		logger.Info("metrics server starting", zap.String("addr", cfg.MetricsListenAddr))
		metricsServer := &http.Server{
			Addr:    cfg.MetricsListenAddr,
			Handler: promhttp.Handler(),
		}
		if err := metricsServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("metrics server error", zap.Error(err))
		}
	}()

	// Start main HTTP server
	go func() {
		logger.Info("http server starting", zap.String("addr", cfg.ListenAddr))
		if err := httpServer.ListenAndServe(cfg.ListenAddr); err != nil {
			logger.Error("server error", zap.Error(err))
		}
	}()

	// Handle graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigChan

	logger.Info("shutdown signal received", zap.String("signal", sig.String()))

	// Graceful shutdown with timeout
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()

	// Flush pending Kafka messages
	logger.Info("flushing kafka messages")
	flushed := kafkaProducer.Flush(30000)
	logger.Info("kafka messages flushed", zap.Int("remaining", flushed))

	// Close server
	if err := httpServer.ShutdownWithContext(shutdownCtx); err != nil {
		logger.Error("server shutdown error", zap.Error(err))
	}

	logger.Info("server stopped")
}

// fastHTTPLogger adapts zap logger to fasthttp Logger interface
type fastHTTPLogger struct {
	logger *zap.Logger
}

func (l *fastHTTPLogger) Printf(format string, args ...interface{}) {
	l.logger.Debug(fmt.Sprintf(format, args...))
}
