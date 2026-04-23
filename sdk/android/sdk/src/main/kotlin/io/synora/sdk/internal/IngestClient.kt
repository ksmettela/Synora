package io.synora.sdk.internal

import android.util.Log
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets

/**
 * Tiny HTTPS client for the ingestor. Uses HttpURLConnection (no extra deps)
 * to keep the SDK binary lean. A production deployment would prefer OkHttp
 * (connection pooling, better timeouts, TLS pinning support).
 */
internal class IngestClient(
    private val serverUrl: String,
    private val apiKey: String,
    private val deviceId: String,
    private val manufacturer: String,
    private val model: String,
) {
    /**
     * POST a batch of fingerprints. Returns true on 2xx, false otherwise
     * (which leaves the rows in the cache for the next retry).
     */
    fun submit(rows: List<FingerprintCache.Row>): Boolean {
        if (rows.isEmpty()) return true

        val body = buildJson(rows)
        val url = URL("${serverUrl.trimEnd('/')}/v1/fingerprints")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 10_000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Authorization", "Bearer $apiKey")
            setRequestProperty("X-Device-Id", deviceId)
            setRequestProperty("X-Manufacturer", manufacturer)
            setRequestProperty("X-Model", model)
            setRequestProperty("User-Agent", "synora-sdk-android/1.0")
        }
        return try {
            conn.outputStream.use { it.write(body.toByteArray(StandardCharsets.UTF_8)) }
            val code = conn.responseCode
            if (code in 200..299) {
                true
            } else {
                Log.w(TAG, "ingestor returned HTTP $code")
                false
            }
        } catch (t: Throwable) {
            Log.w(TAG, "submit failed", t)
            false
        } finally {
            conn.disconnect()
        }
    }

    private fun buildJson(rows: List<FingerprintCache.Row>): String {
        val sb = StringBuilder()
        sb.append("{\"device_id\":\"").append(escape(deviceId)).append("\",\"fingerprints\":[")
        rows.forEachIndexed { index, row ->
            if (index > 0) sb.append(',')
            sb.append("{\"fingerprint_hash\":\"").append(escape(row.fingerprintHex))
            sb.append("\",\"captured_at_ms\":").append(row.capturedAtMs).append('}')
        }
        sb.append("]}")
        return sb.toString()
    }

    private fun escape(s: String): String {
        val sb = StringBuilder(s.length + 8)
        for (ch in s) {
            when (ch) {
                '"' -> sb.append("\\\"")
                '\\' -> sb.append("\\\\")
                '\n' -> sb.append("\\n")
                '\r' -> sb.append("\\r")
                '\t' -> sb.append("\\t")
                else -> if (ch.code < 0x20) sb.append("\\u%04x".format(ch.code)) else sb.append(ch)
            }
        }
        return sb.toString()
    }

    companion object {
        private const val TAG = "SynoraIngestClient"
    }
}
