package io.synora.sdk

import android.content.Context
import android.os.Build
import android.util.Log
import io.synora.sdk.internal.AudioCapturer
import io.synora.sdk.internal.ConsentStore
import io.synora.sdk.internal.DeviceIdentity
import io.synora.sdk.internal.FingerprintCache
import io.synora.sdk.internal.IngestClient
import io.synora.sdk.internal.NativeFingerprint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/**
 * Synora SDK for Android TV.
 *
 * Integration pattern:
 * ```
 * val sdk = SynoraSdk(context, SynoraSdk.Config(
 *     serverUrl = "https://ingest.synora.example",
 *     apiKey = "mfr_abc123",
 * ))
 * sdk.setConsent(true)     // after the user opts in via manufacturer UI
 * sdk.start()
 * // ... later ...
 * sdk.stop()
 * ```
 *
 * This is an OEM-facing SDK: it assumes the manufacturer app holds
 * RECORD_AUDIO and INTERNET permissions, and is responsible for the user-
 * facing consent flow.
 */
class SynoraSdk(
    context: Context,
    private val config: Config,
) {
    data class Config(
        val serverUrl: String,
        val apiKey: String,
        val sampleRateHz: Int = 16_000,
        val captureDurationMs: Int = 3_000,
        val captureIntervalSec: Int = 30,
        val batchSize: Int = 20,
        val flushIntervalSec: Int = 60,
        val manufacturer: String = Build.MANUFACTURER ?: "Unknown",
        val model: String = Build.MODEL ?: "Unknown",
    )

    private val appContext = context.applicationContext
    private val consent = ConsentStore(appContext)
    private val cache = FingerprintCache(appContext)
    private val capturer = AudioCapturer(config.sampleRateHz)
    private val deviceId: String = DeviceIdentity.deviceId(appContext)
    private val ingest = IngestClient(
        serverUrl = config.serverUrl,
        apiKey = config.apiKey,
        deviceId = deviceId,
        manufacturer = config.manufacturer,
        model = config.model,
    )

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val lifecycleMutex = Mutex()
    private var captureJob: Job? = null
    private var uploadJob: Job? = null

    fun setConsent(optedIn: Boolean) {
        consent.optedIn = optedIn
        if (!optedIn) {
            // Immediate purge is required by CCPA — do not wait for the next
            // capture tick.
            scope.launch { cache.purgeAll() }
            scope.launch { stopInternal() }
        }
    }

    fun isOptedIn(): Boolean = consent.optedIn

    fun deviceId(): String = deviceId

    /**
     * Start capturing and uploading fingerprints. No-op if consent not
     * granted.
     */
    fun start() {
        if (!consent.optedIn) {
            Log.w(TAG, "start ignored: user not opted in")
            return
        }
        scope.launch {
            lifecycleMutex.withLock {
                if (captureJob?.isActive == true) return@withLock
                captureJob = scope.launch { captureLoop() }
                uploadJob = scope.launch { uploadLoop() }
            }
        }
    }

    fun stop() {
        scope.launch { stopInternal() }
    }

    private suspend fun stopInternal() {
        lifecycleMutex.withLock {
            captureJob?.cancel()
            captureJob = null
            uploadJob?.cancel()
            uploadJob = null
        }
    }

    private suspend fun captureLoop() {
        val engineRate = config.sampleRateHz
        while (scope.isActive) {
            if (!consent.optedIn) {
                return
            }
            val pcm = withContext(Dispatchers.IO) {
                capturer.capture(config.captureDurationMs)
            }
            if (pcm != null) {
                val bytes = NativeFingerprint.fingerprint(pcm, engineRate)
                if (bytes != null && bytes.size == 32) {
                    val hex = bytes.joinToString("") { "%02x".format(it) }
                    withContext(Dispatchers.IO) {
                        cache.insert(hex, System.currentTimeMillis())
                    }
                }
            }
            delay(config.captureIntervalSec * 1000L)
        }
    }

    private suspend fun uploadLoop() {
        while (scope.isActive) {
            delay(config.flushIntervalSec * 1000L)
            if (!consent.optedIn) continue
            val batch = withContext(Dispatchers.IO) { cache.drainBatch(config.batchSize) }
            if (batch.isEmpty()) continue
            val ok = withContext(Dispatchers.IO) { ingest.submit(batch) }
            if (ok) {
                withContext(Dispatchers.IO) { cache.remove(batch.map { it.id }) }
            }
        }
    }

    companion object {
        private const val TAG = "SynoraSdk"
        const val VERSION: String = "1.0.0"
    }
}
