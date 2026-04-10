// +build integration

package tests

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"testing"
	"time"
)

// Integration tests require running services (Kafka, Redis)
// Run with: go test -v -tags=integration ./tests/...

const (
	baseURL = "http://localhost:8080"
	apiKey  = "test-key"
)

// TestIntegrationHealthCheck tests the health endpoint
func TestIntegrationHealthCheck(t *testing.T) {
	resp, err := http.Get(baseURL + "/health")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var body map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if body["status"] != "ok" {
		t.Errorf("expected status 'ok', got %v", body["status"])
	}
}

// TestIntegrationIngestValid tests valid fingerprint ingestion
func TestIntegrationIngestValid(t *testing.T) {
	batch := FingerprintBatch{
		Batch: []map[string]interface{}{
			{
				"device_id":        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
				"fingerprint_hash": "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
				"timestamp_utc":    time.Now().UnixMilli(),
				"manufacturer":     "LG",
				"model":            "OLED55C3",
				"ip_address":       "192.168.1.100",
			},
		},
	}

	body, _ := json.Marshal(batch)

	req, _ := http.NewRequest("POST", baseURL+"/v1/fingerprints", bytes.NewReader(body))
	req.Header.Set("X-API-Key", apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		body, _ := io.ReadAll(resp.Body)
		t.Errorf("expected 202, got %d: %s", resp.StatusCode, string(body))
	}
}

// TestIntegrationMissingAPIKey tests missing authentication
func TestIntegrationMissingAPIKey(t *testing.T) {
	batch := FingerprintBatch{
		Batch: []map[string]interface{}{
			{
				"device_id":        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
				"fingerprint_hash": "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
				"timestamp_utc":    time.Now().UnixMilli(),
				"manufacturer":     "LG",
				"model":            "OLED55C3",
				"ip_address":       "192.168.1.100",
			},
		},
	}

	body, _ := json.Marshal(batch)

	req, _ := http.NewRequest("POST", baseURL+"/v1/fingerprints", bytes.NewReader(body))
	// Don't set X-API-Key header
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusUnauthorized {
		t.Errorf("expected 401, got %d", resp.StatusCode)
	}
}

// TestIntegrationLargeBatch tests oversized batch rejection
func TestIntegrationLargeBatch(t *testing.T) {
	batch := FingerprintBatch{
		Batch: make([]map[string]interface{}, 150),
	}

	for i := 0; i < 150; i++ {
		batch.Batch[i] = map[string]interface{}{
			"device_id":        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
			"fingerprint_hash": "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
			"timestamp_utc":    time.Now().UnixMilli(),
			"manufacturer":     "LG",
			"model":            "OLED55C3",
			"ip_address":       "192.168.1.100",
		}
	}

	body, _ := json.Marshal(batch)

	req, _ := http.NewRequest("POST", baseURL+"/v1/fingerprints", bytes.NewReader(body))
	req.Header.Set("X-API-Key", apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", resp.StatusCode)
	}
}

// TestIntegrationMetrics tests prometheus metrics endpoint
func TestIntegrationMetrics(t *testing.T) {
	resp, err := http.Get("http://localhost:9090/metrics")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	content := string(body)

	if !contains(content, "acraas_ingest_requests_total") {
		t.Error("expected acraas_ingest_requests_total metric")
	}

	if !contains(content, "acraas_ingest_request_duration_seconds") {
		t.Error("expected acraas_ingest_request_duration_seconds metric")
	}
}

// TestIntegrationMethodNotAllowed tests incorrect HTTP method
func TestIntegrationMethodNotAllowed(t *testing.T) {
	resp, err := http.Get(baseURL + "/v1/fingerprints")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("expected 405, got %d", resp.StatusCode)
	}
}

// TestIntegrationInvalidJSON tests malformed request body
func TestIntegrationInvalidJSON(t *testing.T) {
	req, _ := http.NewRequest("POST", baseURL+"/v1/fingerprints", bytes.NewReader([]byte("invalid json")))
	req.Header.Set("X-API-Key", apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", resp.StatusCode)
	}
}

// TestIntegrationNotFound tests undefined endpoint
func TestIntegrationNotFound(t *testing.T) {
	resp, err := http.Get(baseURL + "/undefined")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404, got %d", resp.StatusCode)
	}
}

// Helper function
func contains(s, substr string) bool {
	return bytes.Contains([]byte(s), []byte(substr))
}

// BenchmarkIntegrationIngest benchmarks the full ingestion pipeline
func BenchmarkIntegrationIngest(b *testing.B) {
	batch := FingerprintBatch{
		Batch: []map[string]interface{}{
			{
				"device_id":        "a" + "0" + string(bytes.Repeat([]byte{48}, 62)),
				"fingerprint_hash": "b" + "1" + string(bytes.Repeat([]byte{49}, 62)),
				"timestamp_utc":    time.Now().UnixMilli(),
				"manufacturer":     "LG",
				"model":            "OLED55C3",
				"ip_address":       "192.168.1.100",
			},
		},
	}

	body, _ := json.Marshal(batch)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("POST", baseURL+"/v1/fingerprints", bytes.NewReader(body))
		req.Header.Set("X-API-Key", apiKey)
		req.Header.Set("Content-Type", "application/json")

		resp, _ := http.DefaultClient.Do(req)
		resp.Body.Close()
	}
}
