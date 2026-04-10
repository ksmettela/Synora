package ratelimit

import (
	"context"
	"fmt"
	"time"

	"github.com/go-redis/redis/v9"
)

// Limiter implements Redis-backed sliding window rate limiting
type Limiter struct {
	client          *redis.Client
	limitPerSecond  int
	windowDuration  time.Duration
}

// RateLimitResult holds the result of a rate limit check
type RateLimitResult struct {
	Allowed      bool
	CurrentCount int
	RetryAfterMS int
}

// NewLimiter creates a new rate limiter
func NewLimiter(client *redis.Client, limitPerSecond int) *Limiter {
	return &Limiter{
		client:         client,
		limitPerSecond: limitPerSecond,
		windowDuration: time.Second,
	}
}

// Allow checks if a request is allowed and updates the sliding window
// Uses ZADD + ZREMRANGEBYSCORE + ZCARD pattern for atomic operations
func (l *Limiter) Allow(ctx context.Context, apiKey string) (*RateLimitResult, error) {
	now := time.Now()
	timestamp := now.UnixMilli()
	windowStart := now.Add(-l.windowDuration).UnixMilli()

	key := fmt.Sprintf("ratelimit:%s:%d", apiKey, now.Unix())

	// Use pipeline for atomic operations
	pipe := l.client.Pipeline()

	// Add current request with timestamp as score (enables sliding window)
	pipe.ZAdd(ctx, key, redis.Z{
		Score:  float64(timestamp),
		Member: timestamp,
	})

	// Remove entries outside the sliding window
	pipe.ZRemRangeByScore(ctx, key, "-inf", fmt.Sprintf("(%d", windowStart))

	// Get current count
	cardCmd := pipe.ZCard(ctx, key)

	// Set expiration to prevent key buildup
	pipe.Expire(ctx, key, 2*l.windowDuration)

	_, err := pipe.Exec(ctx)
	if err != nil {
		return nil, fmt.Errorf("pipeline execution failed: %w", err)
	}

	currentCount, err := cardCmd.Val(), cardCmd.Err()
	if err != nil {
		return nil, fmt.Errorf("failed to get card: %w", err)
	}

	allowed := currentCount <= int64(l.limitPerSecond)
	var retryAfterMS int
	if !allowed {
		retryAfterMS = 1000 / l.limitPerSecond
	}

	return &RateLimitResult{
		Allowed:      allowed,
		CurrentCount: int(currentCount),
		RetryAfterMS: retryAfterMS,
	}, nil
}
