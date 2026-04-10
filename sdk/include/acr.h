/**
 * Synora SDK - Automatic Content Recognition as a Service
 * Public C ABI Header
 *
 * This is the public interface for TV manufacturers to embed
 * in their firmware for automatic content recognition.
 */

#ifndef ACR_H
#define ACR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Version string */
#define ACR_SDK_VERSION "1.0.0"

/**
 * ACR Configuration Structure
 *
 * All string fields must remain valid for the lifetime of initialization.
 */
typedef struct {
    /** Ingest server URL (e.g., "https://acr-ingest.example.com") */
    const char* server_url;

    /** API key for authentication */
    const char* api_key;

    /** Number of fingerprints to batch before transmission (default: 20) */
    int batch_size;

    /** Interval in seconds to flush cached fingerprints (default: 60) */
    int flush_interval_sec;

    /** Audio sample rate in Hz (default: 16000) */
    int sample_rate_hz;

    /** Audio capture duration per sample in milliseconds (default: 3000) */
    int capture_duration_ms;

    /** Interval in seconds between capture cycles (default: 30) */
    int capture_interval_sec;
} acr_config_t;

/**
 * Error Codes
 */
typedef enum {
    ACR_SUCCESS = 0,                   /** Operation successful */
    ACR_ERROR_INIT = -1,               /** Initialization failed */
    ACR_ERROR_NETWORK = -2,            /** Network error */
    ACR_ERROR_CONSENT = -3,            /** User consent not granted */
    ACR_ERROR_AUDIO = -4,              /** Audio capture error */
} acr_error_t;

/**
 * Initialize the ACR SDK
 *
 * Must be called before any other API function.
 *
 * @param config Configuration structure (required, must remain valid)
 * @return ACR_SUCCESS on success, error code otherwise
 */
acr_error_t acr_init(const acr_config_t* config);

/**
 * Start ACR capture and transmission
 *
 * Begins capturing audio and transmitting fingerprints.
 * Respects the user consent setting.
 *
 * @return ACR_SUCCESS on success, error code otherwise
 */
acr_error_t acr_start(void);

/**
 * Stop ACR capture and transmission
 *
 * Stops all background threads and flushes remaining cache.
 *
 * @return ACR_SUCCESS on success, error code otherwise
 */
acr_error_t acr_stop(void);

/**
 * Set user consent for ACR
 *
 * When set to false, clears all cached fingerprints and stops capture.
 * When set to true, resumes capture on next acr_start().
 *
 * @param opted_in true to enable ACR, false to disable
 * @return ACR_SUCCESS on success, error code otherwise
 */
acr_error_t acr_set_consent(bool opted_in);

/**
 * Force immediate transmission of cached fingerprints
 *
 * @return ACR_SUCCESS on success, error code otherwise
 */
acr_error_t acr_flush(void);

/**
 * Get the stable device ID
 *
 * @param buf Output buffer for device ID string (null-terminated)
 * @param len Length of buffer (minimum 64 bytes recommended)
 * @return ACR_SUCCESS on success, error code otherwise
 */
acr_error_t acr_get_device_id(char* buf, size_t len);

/**
 * Get SDK version string
 *
 * @return Version string (e.g., "1.0.0")
 */
const char* acr_version(void);

#ifdef __cplusplus
}
#endif

#endif /* ACR_H */
