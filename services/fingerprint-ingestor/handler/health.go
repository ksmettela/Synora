package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-redis/redis/v9"
	"github.com/valyala/fasthttp"
	"go.uber.org/zap"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// HealthHandler handles health checks
type HealthHandler struct {
	redisClient *redis.Client
	logger      *zap.Logger
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status string `json:"status"`
	Kafka  string `json:"kafka"`
	Redis  string `json:"redis"`
	Time   string `json:"time"`
}

// NewHealthHandler creates a new health handler
func NewHealthHandler(redisClient *redis.Client, logger *zap.Logger) *HealthHandler {
	return &HealthHandler{
		redisClient: redisClient,
		logger:      logger,
	}
}

// Health handles GET /health requests
func (h *HealthHandler) Health(ctx *fasthttp.RequestCtx) {
	response := &HealthResponse{
		Status: "ok",
		Kafka:  "ok", // In real implementation, check broker connectivity
		Redis:  h.checkRedis(),
		Time:   time.Now().UTC().Format(time.RFC3339),
	}

	if response.Kafka == "error" || response.Redis == "error" {
		response.Status = "degraded"
		ctx.SetStatusCode(fasthttp.StatusServiceUnavailable)
	} else {
		ctx.SetStatusCode(fasthttp.StatusOK)
	}

	ctx.SetContentType("application/json")
	json.NewEncoder(ctx).Encode(response)
}

// checkRedis checks Redis connectivity
func (h *HealthHandler) checkRedis() string {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	err := h.redisClient.Ping(ctx).Err()
	if err != nil {
		h.logger.Error("redis health check failed", zap.Error(err))
		return "error"
	}
	return "ok"
}

// MetricsHandler wraps the Prometheus metrics handler
func MetricsHandler(ctx *fasthttp.RequestCtx) {
	promhttp.Handler().ServeHTTP(ctx, &ctx.Request)
}
