package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"github.com/go-redis/redis/v9"
	"github.com/valyala/fasthttp"
	"go.uber.org/zap"

	"github.com/synora/acraas/services/fingerprint-ingestor/geoip"
	"github.com/synora/acraas/services/fingerprint-ingestor/handler"
	"github.com/synora/acraas/services/fingerprint-ingestor/kafka"
	"github.com/synora/acraas/services/fingerprint-ingestor/middleware"
	"github.com/synora/acraas/services/fingerprint-ingestor/ratelimit"
)

// TestData for integration tests
type FingerprintBatch struct {
	Batch []handler.FingerprintEvent `json:"batch"`
}

// mockKafkaProducer is a mock for testing
type mockKafkaProducer struct {
	messages []*kafka.FingerprintMessage
}

func (m *mockKafkaProducer) PublishAsync(msg *kafka.FingerprintMessage) error {
	m.messages = append(m.messages, msg)
	return nil
}

func (m *mockKafkaProducer) PublishBatch(messages []*kafka.FingerprintMessage) error {
	m.messages = append(m.messages, messages...)
	return nil
}

func (m *mockKafkaProducer) Flush(timeoutMs int) int {
	return 0
}

func (m *mockKafkaProducer) Close() error {
	return nil
}

func (m *mockKafkaProducer) GetMetrics() map[string]interface{} {
	return nil
}

// Helper to create test request context
func createTestRequest(body []byte) *fasthttp.RequestCtx {
	ctx := &fasthttp.RequestCtx{}
	ctx.Request.Header.SetMethod("POST")
	ctx.Request.SetBody(body)
	ctx.Request.Header.Set("X-API-Key", "test-key")
	return ctx
}

// Test: Happy path - valid batch returns 202
func TestIngestHappyPath(t *testing.T) {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// Create test batch
	batch := FingerprintBatch{
		Batch: []handler.FingerprintEvent{
			{
				DeviceID:        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
				FingerprintHash: "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
				TimestampUTC:    time.Now().UnixMilli(),
				Manufacturer:    "LG",
				Model:           "OLED55C3",
				IPAddress:       "192.168.1.1",
			},
		},
	}

	body, err := json.Marshal(batch)
	if err != nil {
		t.Fatalf("failed to marshal batch: %v", err)
	}

	// Setup components
	mockProducer := &mockKafkaProducer{}
	mockRedisClient := &redis.Client{} // Would need real Redis for full test
	limiter := ratelimit.NewLimiter(mockRedisClient, 10000)
	geoIPFilter, _ := geoip.NewFilter("", logger)

	ingestHandler := handler.NewIngestHandler(
		mockProducer,
		limiter,
		geoIPFilter,
		logger,
		100,
		300,
	)

	ctx := createTestRequest(body)
	ingestHandler.Handle(ctx)

	// Verify response
	if ctx.Response.StatusCode() != fasthttp.StatusAccepted {
		t.Errorf("expected status %d, got %d", fasthttp.StatusAccepted, ctx.Response.StatusCode())
	}

	// Verify message was queued
	if len(mockProducer.messages) == 0 {
		t.Error("expected message to be published")
	}
}

// Test: Invalid device_id format returns 400
func TestIngestInvalidDeviceID(t *testing.T) {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// Create batch with invalid device_id (not 64-char hex)
	batch := FingerprintBatch{
		Batch: []handler.FingerprintEvent{
			{
				DeviceID:        "invalid-device-id",
				FingerprintHash: "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
				TimestampUTC:    time.Now().UnixMilli(),
				Manufacturer:    "LG",
				Model:           "OLED55C3",
				IPAddress:       "192.168.1.1",
			},
		},
	}

	body, err := json.Marshal(batch)
	if err != nil {
		t.Fatalf("failed to marshal batch: %v", err)
	}

	mockProducer := &mockKafkaProducer{}
	mockRedisClient := &redis.Client{}
	limiter := ratelimit.NewLimiter(mockRedisClient, 10000)
	geoIPFilter, _ := geoip.NewFilter("", logger)

	ingestHandler := handler.NewIngestHandler(
		mockProducer,
		limiter,
		geoIPFilter,
		logger,
		100,
		300,
	)

	ctx := createTestRequest(body)
	ingestHandler.Handle(ctx)

	// All events should be rejected, but 202 still returned
	if ctx.Response.StatusCode() != fasthttp.StatusAccepted {
		t.Errorf("expected status %d, got %d", fasthttp.StatusAccepted, ctx.Response.StatusCode())
	}

	// No messages should be published
	if len(mockProducer.messages) != 0 {
		t.Error("expected no messages to be published for invalid device_id")
	}
}

// Test: Timestamp too old returns no processing
func TestIngestTimestampTooOld(t *testing.T) {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// Create batch with timestamp older than 5 minutes
	oldTimestamp := time.Now().Add(-10 * time.Minute).UnixMilli()

	batch := FingerprintBatch{
		Batch: []handler.FingerprintEvent{
			{
				DeviceID:        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
				FingerprintHash: "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
				TimestampUTC:    oldTimestamp,
				Manufacturer:    "LG",
				Model:           "OLED55C3",
				IPAddress:       "192.168.1.1",
			},
		},
	}

	body, err := json.Marshal(batch)
	if err != nil {
		t.Fatalf("failed to marshal batch: %v", err)
	}

	mockProducer := &mockKafkaProducer{}
	mockRedisClient := &redis.Client{}
	limiter := ratelimit.NewLimiter(mockRedisClient, 10000)
	geoIPFilter, _ := geoip.NewFilter("", logger)

	ingestHandler := handler.NewIngestHandler(
		mockProducer,
		limiter,
		geoIPFilter,
		logger,
		100,
		300, // 300 seconds = 5 minutes
	)

	ctx := createTestRequest(body)
	ingestHandler.Handle(ctx)

	// Still returns 202
	if ctx.Response.StatusCode() != fasthttp.StatusAccepted {
		t.Errorf("expected status %d, got %d", fasthttp.StatusAccepted, ctx.Response.StatusCode())
	}

	// No messages should be published
	if len(mockProducer.messages) != 0 {
		t.Error("expected no messages for timestamp out of range")
	}
}

// Test: Large batch exceeds max size
func TestIngestLargeBatch(t *testing.T) {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// Create batch with 150 items (exceeds max of 100)
	batch := FingerprintBatch{
		Batch: make([]handler.FingerprintEvent, 150),
	}

	for i := 0; i < 150; i++ {
		batch.Batch[i] = handler.FingerprintEvent{
			DeviceID:        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
			FingerprintHash: "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
			TimestampUTC:    time.Now().UnixMilli(),
			Manufacturer:    "LG",
			Model:           "OLED55C3",
			IPAddress:       "192.168.1.1",
		}
	}

	body, err := json.Marshal(batch)
	if err != nil {
		t.Fatalf("failed to marshal batch: %v", err)
	}

	mockProducer := &mockKafkaProducer{}
	mockRedisClient := &redis.Client{}
	limiter := ratelimit.NewLimiter(mockRedisClient, 10000)
	geoIPFilter, _ := geoip.NewFilter("", logger)

	ingestHandler := handler.NewIngestHandler(
		mockProducer,
		limiter,
		geoIPFilter,
		logger,
		100, // Max 100
		300,
	)

	ctx := createTestRequest(body)
	ingestHandler.Handle(ctx)

	// Should return 400 Bad Request
	if ctx.Response.StatusCode() != fasthttp.StatusBadRequest {
		t.Errorf("expected status %d, got %d", fasthttp.StatusBadRequest, ctx.Response.StatusCode())
	}
}

// Test: Invalid fingerprint hash format
func TestIngestInvalidFingerprintHash(t *testing.T) {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	batch := FingerprintBatch{
		Batch: []handler.FingerprintEvent{
			{
				DeviceID:        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
				FingerprintHash: "not-valid-hex",
				TimestampUTC:    time.Now().UnixMilli(),
				Manufacturer:    "LG",
				Model:           "OLED55C3",
				IPAddress:       "192.168.1.1",
			},
		},
	}

	body, err := json.Marshal(batch)
	if err != nil {
		t.Fatalf("failed to marshal batch: %v", err)
	}

	mockProducer := &mockKafkaProducer{}
	mockRedisClient := &redis.Client{}
	limiter := ratelimit.NewLimiter(mockRedisClient, 10000)
	geoIPFilter, _ := geoip.NewFilter("", logger)

	ingestHandler := handler.NewIngestHandler(
		mockProducer,
		limiter,
		geoIPFilter,
		logger,
		100,
		300,
	)

	ctx := createTestRequest(body)
	ingestHandler.Handle(ctx)

	// Should still return 202 (validation happens in batch, not upfront)
	if ctx.Response.StatusCode() != fasthttp.StatusAccepted {
		t.Errorf("expected status %d, got %d", fasthttp.StatusAccepted, ctx.Response.StatusCode())
	}

	// No messages should be published
	if len(mockProducer.messages) != 0 {
		t.Error("expected no messages for invalid fingerprint hash")
	}
}

// Test: Multiple valid events in batch
func TestIngestMultipleEvents(t *testing.T) {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	batch := FingerprintBatch{
		Batch: []handler.FingerprintEvent{
			{
				DeviceID:        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
				FingerprintHash: "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
				TimestampUTC:    time.Now().UnixMilli(),
				Manufacturer:    "LG",
				Model:           "OLED55C3",
				IPAddress:       "192.168.1.1",
			},
			{
				DeviceID:        "c" + "2" + string(bytes.Repeat([]byte{50}, 62)),
				FingerprintHash: "d" + "3" + string(bytes.Repeat([]byte{51}, 62)),
				TimestampUTC:    time.Now().UnixMilli(),
				Manufacturer:    "Samsung",
				Model:           "UN55AU8000",
				IPAddress:       "10.0.0.1",
			},
		},
	}

	body, err := json.Marshal(batch)
	if err != nil {
		t.Fatalf("failed to marshal batch: %v", err)
	}

	mockProducer := &mockKafkaProducer{}
	mockRedisClient := &redis.Client{}
	limiter := ratelimit.NewLimiter(mockRedisClient, 10000)
	geoIPFilter, _ := geoip.NewFilter("", logger)

	ingestHandler := handler.NewIngestHandler(
		mockProducer,
		limiter,
		geoIPFilter,
		logger,
		100,
		300,
	)

	ctx := createTestRequest(body)
	ingestHandler.Handle(ctx)

	// Should return 202
	if ctx.Response.StatusCode() != fasthttp.StatusAccepted {
		t.Errorf("expected status %d, got %d", fasthttp.StatusAccepted, ctx.Response.StatusCode())
	}

	// Both messages should be published
	if len(mockProducer.messages) != 2 {
		t.Errorf("expected 2 messages, got %d", len(mockProducer.messages))
	}
}

// Benchmark for high throughput testing
func BenchmarkIngest(b *testing.B) {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	mockProducer := &mockKafkaProducer{}
	mockRedisClient := &redis.Client{}
	limiter := ratelimit.NewLimiter(mockRedisClient, 10000)
	geoIPFilter, _ := geoip.NewFilter("", logger)

	ingestHandler := handler.NewIngestHandler(
		mockProducer,
		limiter,
		geoIPFilter,
		logger,
		100,
		300,
	)

	batch := FingerprintBatch{
		Batch: []handler.FingerprintEvent{
			{
				DeviceID:        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
				FingerprintHash: "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
				TimestampUTC:    time.Now().UnixMilli(),
				Manufacturer:    "LG",
				Model:           "OLED55C3",
				IPAddress:       "192.168.1.1",
			},
		},
	}

	body, _ := json.Marshal(batch)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ctx := createTestRequest(body)
		ingestHandler.Handle(ctx)
	}
}
