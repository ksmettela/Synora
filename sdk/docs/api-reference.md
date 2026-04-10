# ACRaaS SDK - API Reference

## C API (acr.h)

### Configuration Structure

```c
typedef struct {
    const char* server_url;        // Ingest server URL
    const char* api_key;           // API key for auth
    int batch_size;                // Fingerprints per batch (default: 20)
    int flush_interval_sec;        // Cache flush interval (default: 60)
    int sample_rate_hz;            // Audio sample rate (default: 16000)
    int capture_duration_ms;       // Capture duration (default: 3000)
    int capture_interval_sec;      // Capture interval (default: 30)
} acr_config_t;
```

### Error Codes

```c
enum acr_error_t {
    ACR_SUCCESS = 0,               // Operation successful
    ACR_ERROR_INIT = -1,           // Initialization failed
    ACR_ERROR_NETWORK = -2,        // Network error
    ACR_ERROR_CONSENT = -3,        // Consent not granted
    ACR_ERROR_AUDIO = -4,          // Audio capture error
};
```

### Functions

#### acr_init()

Initialize the ACR SDK. Must be called before any other function.

```c
acr_error_t acr_init(const acr_config_t* config);
```

**Parameters:**
- `config`: Configuration structure (required, must remain valid)

**Returns:**
- `ACR_SUCCESS` on success
- Error code on failure

**Notes:**
- Can only be called once per process
- Initializes all subsystems (device ID, cache, audio, network)
- Validates configuration parameters

**Example:**
```c
acr_config_t config = {
    .server_url = "https://acr.example.com",
    .api_key = "key123",
};

if (acr_init(&config) != ACR_SUCCESS) {
    fprintf(stderr, "Init failed\n");
    return 1;
}
```

---

#### acr_start()

Start audio capture and fingerprint transmission.

```c
acr_error_t acr_start(void);
```

**Returns:**
- `ACR_SUCCESS` on success
- `ACR_ERROR_INIT` if not initialized
- `ACR_ERROR_CONSENT` if user opted out
- `ACR_ERROR_AUDIO` if capture fails

**Notes:**
- Respects user consent setting
- Starts background audio capture thread
- Starts background network transmission thread
- Idempotent (calling multiple times is safe)

**Example:**
```c
if (acr_start() != ACR_SUCCESS) {
    fprintf(stderr, "Start failed\n");
}
```

---

#### acr_stop()

Stop audio capture and transmission.

```c
acr_error_t acr_stop(void);
```

**Returns:**
- `ACR_SUCCESS` on success
- Error code on failure

**Notes:**
- Gracefully shuts down all threads
- Flushes remaining cached data to server
- Can be called multiple times safely
- After stop, can call acr_start() again to resume

**Example:**
```c
acr_stop();
```

---

#### acr_set_consent()

Set user consent for ACR.

```c
acr_error_t acr_set_consent(bool opted_in);
```

**Parameters:**
- `opted_in`: `true` to enable ACR, `false` to disable

**Returns:**
- `ACR_SUCCESS` on success
- Error code on failure

**Notes:**
- When set to `false`:
  - Stops audio capture immediately
  - Purges all cached fingerprints
  - Clears transmission queue
  - Writes "opted_out" to consent file
- When set to `true`:
  - Allows acr_start() to proceed
  - Does not automatically start capture
- Persistent across reboots

**Example:**
```c
// User enables ACR in TV settings
acr_set_consent(true);

// Later, user disables ACR
// This clears all data
acr_set_consent(false);
```

---

#### acr_flush()

Force immediate transmission of cached fingerprints.

```c
acr_error_t acr_flush(void);
```

**Returns:**
- `ACR_SUCCESS` on success
- `ACR_ERROR_INIT` if not initialized
- `ACR_ERROR_NETWORK` if transmission fails

**Notes:**
- Sends all untransmitted fingerprints immediately
- Does not block (returns immediately)
- Useful before shutdown or user-triggered actions
- Safe to call while capture is running

**Example:**
```c
// Before shutdown
acr_flush();
acr_stop();
```

---

#### acr_get_device_id()

Get the stable device ID.

```c
acr_error_t acr_get_device_id(char* buf, size_t len);
```

**Parameters:**
- `buf`: Output buffer (minimum 64 bytes recommended)
- `len`: Size of buffer

**Returns:**
- `ACR_SUCCESS` on success
- `ACR_ERROR_INIT` if buffer too small or not initialized

**Notes:**
- Returns SHA256 hash as hex string (64 characters)
- Device ID is stable across reboots
- Based on MAC address + manufacturer + model
- Null-terminated string in buffer

**Example:**
```c
char device_id[256];
if (acr_get_device_id(device_id, sizeof(device_id)) == ACR_SUCCESS) {
    printf("Device ID: %s\n", device_id);
}
```

---

#### acr_version()

Get SDK version string.

```c
const char* acr_version(void);
```

**Returns:**
- Version string (e.g., "1.0.0")

**Notes:**
- Can be called anytime, even before acr_init()
- Static string, no need to free
- Semantic versioning (MAJOR.MINOR.PATCH)

**Example:**
```c
printf("ACRaaS SDK version: %s\n", acr_version());
```

---

## Android/Kotlin API

### AcrSdk Object

```kotlin
object AcrSdk {
    data class Config(
        val serverUrl: String,
        val apiKey: String,
        val batchSize: Int = 20,
        val flushIntervalSec: Int = 60,
        val sampleRateHz: Int = 16000,
        val captureDurationMs: Int = 3000,
        val captureIntervalSec: Int = 30
    )

    object ErrorCode {
        const val SUCCESS = 0
        const val ERROR_INIT = -1
        const val ERROR_NETWORK = -2
        const val ERROR_CONSENT = -3
        const val ERROR_AUDIO = -4
    }

    fun init(config: Config): Int
    fun start(): Int
    fun stop(): Int
    fun setConsent(optedIn: Boolean): Int
    fun flush(): Int
    fun getDeviceId(): String
    fun version(): String
}
```

### Kotlin Example

```kotlin
// Initialize
val config = AcrSdk.Config(
    serverUrl = "https://acr.example.com",
    apiKey = "your-api-key"
)
AcrSdk.init(config)

// Start capture
AcrSdk.setConsent(true)
AcrSdk.start()

// Flush when needed
AcrSdk.flush()

// Stop on shutdown
AcrSdk.stop()

// Get device ID
val deviceId = AcrSdk.getDeviceId()
```

---

## Common Patterns

### Initialization and Cleanup

```c
// Initialize at startup
acr_config_t config = { ... };
if (acr_init(&config) != ACR_SUCCESS) {
    return -1;
}

// ... application runs ...

// Cleanup on shutdown
acr_flush();
acr_stop();
```

### Handling Consent Changes

```c
void on_user_consent_changed(bool opted_in) {
    if (acr_set_consent(opted_in) != ACR_SUCCESS) {
        perror("Failed to update consent");
    }
    
    if (opted_in && state == RUNNING) {
        acr_start();
    }
}
```

### Error Handling

```c
acr_error_t err = acr_init(&config);

switch (err) {
    case ACR_SUCCESS:
        printf("OK\n");
        break;
    case ACR_ERROR_INIT:
        fprintf(stderr, "Init failed - check config\n");
        break;
    case ACR_ERROR_NETWORK:
        fprintf(stderr, "Network unavailable\n");
        break;
    case ACR_ERROR_CONSENT:
        fprintf(stderr, "User consent not granted\n");
        break;
    case ACR_ERROR_AUDIO:
        fprintf(stderr, "Audio system not available\n");
        break;
}
```

### Performance Tuning

```c
// Low-power device (capture every 60s)
acr_config_t config = {
    .capture_interval_sec = 60,
    .capture_duration_ms = 2000,
    .batch_size = 10,
    .flush_interval_sec = 120,
};

// High-performance device (frequent sampling)
acr_config_t config = {
    .capture_interval_sec = 15,
    .capture_duration_ms = 5000,
    .batch_size = 50,
    .flush_interval_sec = 30,
};
```

---

## Data Structures

### Fingerprint Entry (Internal)

```c
struct FingerprintCacheEntry {
    int id;                        // Database row ID
    std::string device_id;         // Device identifier
    std::array<uint8_t, 32> fingerprint;  // 256-bit hash
    int64_t timestamp_utc;         // Capture timestamp
    bool transmitted;              // Transmission status
};
```

### Network Payload (JSON)

```json
{
    "device_id": "a1b2c3d4...",
    "manufacturer": "Samsung",
    "model": "UN55MU7000",
    "fingerprints": [
        {
            "timestamp_utc": 1234567890,
            "fingerprint_hex": "deadbeef..."
        }
    ]
}
```

---

## Constants

### Configuration Defaults

| Parameter | Default | Min | Max |
|-----------|---------|-----|-----|
| batch_size | 20 | 1 | 1000 |
| flush_interval_sec | 60 | 5 | 3600 |
| sample_rate_hz | 16000 | 8000 | 48000 |
| capture_duration_ms | 3000 | 500 | 10000 |
| capture_interval_sec | 30 | 5 | 3600 |

### Storage Paths

- Device ID cache: `/var/lib/acr/device_id`
- Fingerprint database: `/var/lib/acr/fingerprint_cache.db`
- Consent file: `/var/lib/acr/consent`

### Network

- HTTP Method: `POST`
- Content-Type: `application/json`
- Endpoint: `/v1/fingerprints/ingest`
- Success Response: `202 Accepted`
- Connection Timeout: `10 seconds`
- Read Timeout: `30 seconds`
- Retry Backoff: `exponential (1s, 2s, 4s, 8s, ..., 300s)`

---

## Thread Safety

All SDK functions are thread-safe:
- Device ID manager: Protected by mutex
- Cache operations: Protected by SQLite transactions
- Network client: Uses background thread with condition variables
- Audio capture: Separate capture thread
- Consent manager: Protected by mutex

It is safe to call SDK functions from multiple threads.

---

## Memory Usage

Typical memory footprint:
- SDK overhead: ~2-5 MB
- Audio buffer: ~0.2 MB (16kHz * 3s)
- Cache (500 fingerprints): ~50 MB max
- Network client: ~1 MB
- **Total: ~10-20 MB resident**

---

## CPU Usage Target

- Capture cycle: < 2% CPU
- Network transmission: < 1% CPU
- Idle: < 0.5% CPU

Configure `capture_interval_sec` to tune CPU usage.
