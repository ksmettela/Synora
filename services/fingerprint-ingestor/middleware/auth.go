package middleware

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/go-redis/redis/v9"
	"github.com/valyala/fasthttp"
	"go.uber.org/zap"
	"github.com/synora/acraas/services/fingerprint-ingestor/metrics"
)

// Auth middleware for API key validation
type Auth struct {
	redisClient   *redis.Client
	logger        *zap.Logger
	localCache    sync.Map // map[string]time.Time
	cacheExpiry   time.Duration
}

// NewAuth creates a new auth middleware
func NewAuth(redisClient *redis.Client, logger *zap.Logger) *Auth {
	return &Auth{
		redisClient: redisClient,
		logger:      logger,
		cacheExpiry: 5 * time.Minute,
	}
}

// Middleware wraps a handler with API key validation
func (a *Auth) Middleware(handler fasthttp.RequestHandler) fasthttp.RequestHandler {
	return func(ctx *fasthttp.RequestCtx) {
		apiKey := string(ctx.Request.Header.Peek("X-API-Key"))

		if apiKey == "" {
			metrics.AuthErrorsTotal.WithLabelValues("missing_key").Inc()
			a.logger.Debug("missing API key")
			ctx.SetStatusCode(fasthttp.StatusUnauthorized)
			ctx.SetContentType("application/json")
			fmt.Fprintf(ctx, `{"error":"missing X-API-Key header"}`)
			return
		}

		if !a.isValidKey(context.Background(), apiKey) {
			metrics.AuthErrorsTotal.WithLabelValues("invalid_key").Inc()
			a.logger.Debug("invalid API key", zap.String("api_key", apiKey))
			ctx.SetStatusCode(fasthttp.StatusForbidden)
			ctx.SetContentType("application/json")
			fmt.Fprintf(ctx, `{"error":"invalid API key"}`)
			return
		}

		// Store API key in context for later use
		ctx.SetUserValue("api_key", apiKey)
		handler(ctx)
	}
}

func (a *Auth) isValidKey(ctx context.Context, apiKey string) bool {
	// Check local cache first
	if cached, ok := a.localCache.Load(apiKey); ok {
		expiry := cached.(time.Time)
		if time.Now().Before(expiry) {
			return true
		}
		a.localCache.Delete(apiKey)
	}

	// Check Redis
	result := a.redisClient.SIsMember(ctx, "valid_api_keys", apiKey)
	if result.Err() != nil {
		a.logger.Error("redis check failed", zap.Error(result.Err()))
		return false
	}

	if result.Val() {
		// Cache the valid key for 5 minutes
		a.localCache.Store(apiKey, time.Now().Add(a.cacheExpiry))
		return true
	}

	return false
}

// AddKey adds an API key to the valid set (for testing/management)
func (a *Auth) AddKey(ctx context.Context, apiKey string) error {
	return a.redisClient.SAdd(ctx, "valid_api_keys", apiKey).Err()
}

// RemoveKey removes an API key from the valid set
func (a *Auth) RemoveKey(ctx context.Context, apiKey string) error {
	return a.redisClient.SRem(ctx, "valid_api_keys", apiKey).Err()
}
