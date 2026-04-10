/**
 * Synora SDK - Kotlin JNI Wrapper for Android TV
 *
 * Provides convenient Kotlin bindings to the native C SDK.
 */

package io.acraas.sdk

/**
 * Main Synora SDK Kotlin wrapper
 *
 * Usage:
 * ```
 * val config = AcrSdk.Config(
 *     serverUrl = "https://acr-ingest.example.com",
 *     apiKey = "your-api-key"
 * )
 * AcrSdk.init(config)
 * AcrSdk.start()
 * // ... later ...
 * AcrSdk.stop()
 * ```
 */
object AcrSdk {
    companion object {
        /**
         * Load native library
         */
        init {
            System.loadLibrary("acr")
        }
    }

    /**
     * Synora SDK Configuration
     *
     * @param serverUrl Ingest server URL (e.g., "https://acr-ingest.example.com")
     * @param apiKey API key for authentication
     * @param batchSize Number of fingerprints per batch (default: 20)
     * @param flushIntervalSec Seconds between cache flushes (default: 60)
     * @param sampleRateHz Audio sample rate in Hz (default: 16000)
     * @param captureDurationMs Duration of each audio capture in ms (default: 3000)
     * @param captureIntervalSec Interval between captures in seconds (default: 30)
     */
    data class Config(
        val serverUrl: String,
        val apiKey: String,
        val batchSize: Int = 20,
        val flushIntervalSec: Int = 60,
        val sampleRateHz: Int = 16000,
        val captureDurationMs: Int = 3000,
        val captureIntervalSec: Int = 30
    )

    /**
     * Error codes returned by SDK operations
     */
    object ErrorCode {
        const val SUCCESS = 0
        const val ERROR_INIT = -1
        const val ERROR_NETWORK = -2
        const val ERROR_CONSENT = -3
        const val ERROR_AUDIO = -4
    }

    /**
     * Initialize the Synora SDK
     *
     * Must be called before any other SDK method.
     *
     * @param config Configuration object
     * @return Error code (0 = success)
     */
    fun init(config: Config): Int {
        return native_init(
            config.serverUrl,
            config.apiKey,
            config.batchSize,
            config.flushIntervalSec,
            config.sampleRateHz,
            config.captureDurationMs,
            config.captureIntervalSec
        )
    }

    /**
     * Start ACR capture and transmission
     *
     * @return Error code (0 = success)
     */
    fun start(): Int {
        return native_start()
    }

    /**
     * Stop ACR capture and transmission
     *
     * @return Error code (0 = success)
     */
    fun stop(): Int {
        return native_stop()
    }

    /**
     * Set user consent for ACR
     *
     * @param optedIn true to enable, false to disable
     * @return Error code (0 = success)
     */
    fun setConsent(optedIn: Boolean): Int {
        return native_set_consent(optedIn)
    }

    /**
     * Force immediate transmission of cached fingerprints
     *
     * @return Error code (0 = success)
     */
    fun flush(): Int {
        return native_flush()
    }

    /**
     * Get the stable device ID
     *
     * @return Device ID string (SHA256 hex hash)
     */
    fun getDeviceId(): String {
        return native_get_device_id()
    }

    /**
     * Get SDK version string
     *
     * @return Version string (e.g., "1.0.0")
     */
    fun version(): String {
        return native_version()
    }

    // Native method declarations
    private external fun native_init(
        serverUrl: String,
        apiKey: String,
        batchSize: Int,
        flushIntervalSec: Int,
        sampleRateHz: Int,
        captureDurationMs: Int,
        captureIntervalSec: Int
    ): Int

    private external fun native_start(): Int

    private external fun native_stop(): Int

    private external fun native_set_consent(optedIn: Boolean): Int

    private external fun native_flush(): Int

    private external fun native_get_device_id(): String

    private external fun native_version(): String
}
