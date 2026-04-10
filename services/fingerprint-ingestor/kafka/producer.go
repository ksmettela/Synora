package kafka

import (
	"encoding/json"
	"fmt"

	"github.com/confluentinc/confluent-kafka-go/v2/kafka"
	"go.uber.org/zap"
	"github.com/synora/acraas/services/fingerprint-ingestor/metrics"
)

// Avro schema definition (informational)
/*
{
  "type": "record",
  "name": "RawFingerprint",
  "namespace": "com.synora.acraas",
  "fields": [
    {"name": "device_id", "type": "string"},
    {"name": "fingerprint_hash", "type": "string"},
    {"name": "timestamp_utc", "type": "long"},
    {"name": "manufacturer", "type": "string"},
    {"name": "model", "type": "string"},
    {"name": "ip_address", "type": "string"},
    {"name": "ingested_at", "type": "long"}
  ]
}
*/

// FingerprintMessage represents a single fingerprint event
type FingerprintMessage struct {
	DeviceID         string `json:"device_id"`
	FingerprintHash  string `json:"fingerprint_hash"`
	TimestampUTC     int64  `json:"timestamp_utc"`
	Manufacturer     string `json:"manufacturer"`
	Model            string `json:"model"`
	IPAddress        string `json:"ip_address"`
	IngestedAt       int64  `json:"ingested_at"`
}

// Producer wraps Kafka producer functionality
type Producer struct {
	producer *kafka.Producer
	topic    string
	logger   *zap.Logger
	errChan  chan error
}

// NewProducer creates a new Kafka producer
func NewProducer(bootstrapServers, topic string, logger *zap.Logger) (*Producer, error) {
	config := &kafka.ConfigMap{
		"bootstrap.servers": bootstrapServers,
		"acks":              "all",
		"retries":           3,
		"linger.ms":         5,
		"compression.type":  "snappy",
		"client.id":         "fingerprint-ingestor",
	}

	p, err := kafka.NewProducer(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kafka producer: %w", err)
	}

	producer := &Producer{
		producer: p,
		topic:    topic,
		logger:   logger,
		errChan:  make(chan error, 1000),
	}

	// Start error channel monitor
	go producer.monitorErrors()

	return producer, nil
}

// PublishAsync publishes a message asynchronously
// Partitioning is done by device_id using the hash partitioner
func (p *Producer) PublishAsync(msg *FingerprintMessage) error {
	data, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("failed to marshal message: %w", err)
	}

	deliveryChan := make(chan kafka.Event, 1)
	err = p.producer.Produce(&kafka.Message{
		TopicPartition: kafka.TopicPartition{
			Topic:     &p.topic,
			Partition: kafka.PartitionAny,
		},
		Key:   []byte(msg.DeviceID), // Partition by device_id
		Value: data,
	}, deliveryChan)

	if err != nil {
		metrics.KafkaPublishErrorsTotal.Inc()
		return fmt.Errorf("failed to produce message: %w", err)
	}

	// Handle delivery report asynchronously
	go func() {
		e := <-deliveryChan
		m := e.(*kafka.Message)
		if m.TopicPartition.Error != nil {
			metrics.KafkaPublishErrorsTotal.Inc()
			p.logger.Error("delivery failed",
				zap.String("device_id", msg.DeviceID),
				zap.Error(m.TopicPartition.Error),
			)
		} else {
			metrics.KafkaMessagesPublished.Inc()
			p.logger.Debug("message delivered",
				zap.String("device_id", msg.DeviceID),
				zap.Int32("partition", m.TopicPartition.Partition),
				zap.Int64("offset", m.TopicPartition.Offset),
			)
		}
		close(deliveryChan)
	}()

	return nil
}

// PublishBatch publishes multiple messages (fire-and-forget style)
func (p *Producer) PublishBatch(messages []*FingerprintMessage) error {
	for _, msg := range messages {
		if err := p.PublishAsync(msg); err != nil {
			return err
		}
	}
	return nil
}

// Flush waits for all pending messages to be delivered
func (p *Producer) Flush(timeoutMs int) int {
	return p.producer.Flush(timeoutMs)
}

// Close gracefully closes the producer
func (p *Producer) Close() error {
	p.producer.Flush(30000) // 30 second timeout
	p.producer.Close()
	close(p.errChan)
	return nil
}

// monitorErrors monitors the error channel for background logging
func (p *Producer) monitorErrors() {
	for err := range p.errChan {
		if err != nil {
			p.logger.Error("kafka background error", zap.Error(err))
		}
	}
}

// GetMetrics returns current producer metrics
func (p *Producer) GetMetrics() map[string]interface{} {
	stats, err := p.producer.GetMetadata(nil, false, 5000)
	if err != nil {
		p.logger.Error("failed to get metadata", zap.Error(err))
		return nil
	}

	return map[string]interface{}{
		"brokers": len(stats.Brokers),
		"topics":  len(stats.Topics),
	}
}
