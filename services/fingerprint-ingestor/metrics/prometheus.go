package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// IngestRequestsTotal counts total ingestion requests
	IngestRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "acraas_ingest_requests_total",
			Help: "Total number of ingestion requests processed",
		},
		[]string{"status", "manufacturer"},
	)

	// IngestRequestDuration measures request processing time
	IngestRequestDuration = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "acraas_ingest_request_duration_seconds",
			Help:    "Request processing duration in seconds",
			Buckets: prometheus.DefBuckets,
		},
	)

	// IngestBatchSize measures fingerprints per batch
	IngestBatchSize = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "acraas_ingest_batch_size",
			Help:    "Number of fingerprints per batch",
			Buckets: []float64{1, 5, 10, 25, 50, 100},
		},
	)

	// KafkaPublishErrorsTotal counts Kafka publish failures
	KafkaPublishErrorsTotal = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "acraas_kafka_publish_errors_total",
			Help: "Total number of Kafka publishing errors",
		},
	)

	// RateLimitRejectionsTotal counts rate limit rejections
	RateLimitRejectionsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "acraas_ratelimit_rejections_total",
			Help: "Total number of rate limit rejections",
		},
		[]string{"api_key"},
	)

	// GeoIPRejectionsTotal counts geoIP-based rejections
	GeoIPRejectionsTotal = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "acraas_geoip_rejections_total",
			Help: "Total number of geoIP-based rejections",
		},
	)

	// ValidationErrorsTotal counts validation errors
	ValidationErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "acraas_validation_errors_total",
			Help: "Total number of validation errors",
		},
		[]string{"error_type"},
	)

	// AuthErrorsTotal counts authentication/authorization errors
	AuthErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "acraas_auth_errors_total",
			Help: "Total number of authentication/authorization errors",
		},
		[]string{"error_type"},
	)

	// KafkaMessagesPublished counts successfully published messages
	KafkaMessagesPublished = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "acraas_kafka_messages_published_total",
			Help: "Total number of successfully published Kafka messages",
		},
	)
)
