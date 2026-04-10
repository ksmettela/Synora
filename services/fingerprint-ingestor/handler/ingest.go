package handler

import (
	"encoding/json"
	"fmt"
	"regexp"
	"sync/atomic"
	"time"

	"github.com/valyala/fasthttp"
	"go.uber.org/zap"
	"github.com/synora/acraas/services/fingerprint-ingestor/geoip"
	"github.com/synora/acraas/services/fingerprint-ingestor/kafka"
	"github.com/synora/acraas/services/fingerprint-ingestor/metrics"
	"github.com/synora/acraas/services/fingerprint-ingestor/ratelimit"
)

// IngestRequest represents the incoming batch request
type IngestRequest struct {
	Batch []FingerprintEvent `json:"batch"`
}

// FingerprintEvent represents a single fingerprint in the batch
type FingerprintEvent struct {
	DeviceID        string `json:"device_id"`
	FingerprintHash string `json:"fingerprint_hash"`
	TimestampUTC    int64  `json:"timestamp_utc"`
	Manufacturer    string `json:"manufacturer"`
	Model           string `json:"model"`
	IPAddress       string `json:"ip_address"`
}

// IngestHandler handles fingerprint ingestion
type IngestHandler struct {
	producer              *kafka.Producer
	rateLimiter           *ratelimit.Limiter
	geoIPFilter           *geoip.Filter
	logger                *zap.Logger
	maxBatchSize          int
	timestampToleranceSec int
	hexRegex              *regexp.Regexp
	requestsProcessed     atomic.Uint64
}

// NewIngestHandler creates a new ingest handler
func NewIngestHandler(
	producer *kafka.Producer,
	rateLimiter *ratelimit.Limiter,
	geoIPFilter *geoip.Filter,
	logger *zap.Logger,
	maxBatchSize int,
	timestampToleranceSec int,
) *IngestHandler {
	return &IngestHandler{
		producer:              producer,
		rateLimiter:           rateLimiter,
		geoIPFilter:           geoIPFilter,
		logger:                logger,
		maxBatchSize:          maxBatchSize,
		timestampToleranceSec: timestampToleranceSec,
		hexRegex:              regexp.MustCompile("^[a-fA-F0-9]{64}$"),
	}
}

// Handle handles POST /v1/fingerprints requests
func (h *IngestHandler) Handle(ctx *fasthttp.RequestCtx) {
	start := time.Now()
	apiKey := ctx.UserValue("api_key").(string)

	// Parse and validate request
	var req IngestRequest
	if err := json.Unmarshal(ctx.PostBody(), &req); err != nil {
		metrics.ValidationErrorsTotal.WithLabelValues("invalid_json").Inc()
		h.logger.Debug("invalid JSON", zap.Error(err))
		ctx.SetStatusCode(fasthttp.StatusBadRequest)
		ctx.SetContentType("application/json")
		fmt.Fprintf(ctx, `{"error":"invalid JSON body"}`)
		return
	}

	// Validate batch size
	if len(req.Batch) == 0 || len(req.Batch) > h.maxBatchSize {
		metrics.ValidationErrorsTotal.WithLabelValues("invalid_batch_size").Inc()
		h.logger.Debug("invalid batch size", zap.Int("size", len(req.Batch)))
		ctx.SetStatusCode(fasthttp.StatusBadRequest)
		ctx.SetContentType("application/json")
		fmt.Fprintf(ctx, `{"error":"batch size must be 1-%d"}`, h.maxBatchSize)
		return
	}

	// Check rate limit
	limitResult, err := h.rateLimiter.Allow(ctx, apiKey)
	if err != nil {
		h.logger.Error("rate limit check failed", zap.Error(err))
		ctx.SetStatusCode(fasthttp.StatusInternalServerError)
		ctx.SetContentType("application/json")
		fmt.Fprintf(ctx, `{"error":"internal error"}`)
		return
	}

	if !limitResult.Allowed {
		metrics.RateLimitRejectionsTotal.WithLabelValues(apiKey).Inc()
		h.logger.Debug("rate limit exceeded", zap.String("api_key", apiKey), zap.Int("current_count", limitResult.CurrentCount))
		ctx.SetStatusCode(fasthttp.StatusTooManyRequests)
		ctx.Response.Header.Add("Retry-After", fmt.Sprintf("%d", limitResult.RetryAfterMS/1000))
		ctx.SetContentType("application/json")
		fmt.Fprintf(ctx, `{"error":"rate limit exceeded"}`)
		return
	}

	// Validate and filter events
	validEvents := make([]*kafka.FingerprintMessage, 0, len(req.Batch))
	manufacturerStats := make(map[string]int)
	now := time.Now()

	for _, event := range req.Batch {
		// Validate device_id format
		if !h.hexRegex.MatchString(event.DeviceID) {
			metrics.ValidationErrorsTotal.WithLabelValues("invalid_device_id").Inc()
			h.logger.Debug("invalid device_id", zap.String("device_id", event.DeviceID))
			continue
		}

		// Validate fingerprint_hash format
		if !h.hexRegex.MatchString(event.FingerprintHash) {
			metrics.ValidationErrorsTotal.WithLabelValues("invalid_fingerprint_hash").Inc()
			h.logger.Debug("invalid fingerprint_hash", zap.String("fingerprint_hash", event.FingerprintHash))
			continue
		}

		// Validate timestamp (within tolerance)
		eventTime := time.Unix(0, event.TimestampUTC*int64(time.Millisecond))
		timeDiff := now.Sub(eventTime).Seconds()
		if timeDiff < 0 || timeDiff > float64(h.timestampToleranceSec) {
			metrics.ValidationErrorsTotal.WithLabelValues("timestamp_out_of_range").Inc()
			h.logger.Debug("timestamp out of range", zap.Int64("timestamp", event.TimestampUTC), zap.Float64("diff_sec", timeDiff))
			continue
		}

		// Validate IP address and check geoIP filter
		if !h.geoIPFilter.IsAllowed(ctx, event.IPAddress) {
			metrics.GeoIPRejectionsTotal.Inc()
			h.logger.Debug("IP rejected by geoIP filter", zap.String("ip", event.IPAddress))
			continue
		}

		// Event is valid, prepare for publishing
		validEvents = append(validEvents, &kafka.FingerprintMessage{
			DeviceID:        event.DeviceID,
			FingerprintHash: event.FingerprintHash,
			TimestampUTC:    event.TimestampUTC,
			Manufacturer:    event.Manufacturer,
			Model:           event.Model,
			IPAddress:       event.IPAddress,
			IngestedAt:      now.UnixMilli(),
		})

		manufacturerStats[event.Manufacturer]++
	}

	// Publish valid events to Kafka (fire-and-forget)
	if len(validEvents) > 0 {
		if err := h.producer.PublishBatch(validEvents); err != nil {
			h.logger.Error("failed to publish batch", zap.Error(err))
			metrics.KafkaPublishErrorsTotal.Inc()
			// Still return 202 - message is queued for retry
		}

		// Record metrics
		metrics.IngestBatchSize.Observe(float64(len(validEvents)))
		for manufacturer, count := range manufacturerStats {
			metrics.IngestRequestsTotal.WithLabelValues("202", manufacturer).Add(float64(count))
		}
	}

	// Always return 202 Accepted immediately (fire-and-forget)
	ctx.SetStatusCode(fasthttp.StatusAccepted)
	ctx.SetContentType("application/json")
	fmt.Fprintf(ctx, `{"status":"accepted","processed":%d,"rejected":%d}`, len(validEvents), len(req.Batch)-len(validEvents))

	// Record timing and request count
	duration := time.Since(start).Seconds()
	metrics.IngestRequestDuration.Observe(duration)
	h.requestsProcessed.Add(1)

	h.logger.Debug("request processed",
		zap.String("api_key", apiKey),
		zap.Int("batch_size", len(req.Batch)),
		zap.Int("valid_events", len(validEvents)),
		zap.Duration("duration", time.Since(start)),
	)
}

// GetStats returns request processing statistics
func (h *IngestHandler) GetStats() map[string]interface{} {
	return map[string]interface{}{
		"requests_processed": h.requestsProcessed.Load(),
	}
}
