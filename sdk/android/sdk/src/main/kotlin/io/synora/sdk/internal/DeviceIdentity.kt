package io.synora.sdk.internal

import android.content.Context
import android.provider.Settings
import java.security.MessageDigest

/**
 * Stable-but-rotatable device ID. We never expose the raw ANDROID_ID (or any
 * hardware identifier) to the cloud; instead we hash it with a monthly-rotating
 * salt. Same device, same month → same ID. New month → fresh ID.
 */
internal object DeviceIdentity {
    @Suppress("HardwareIds")
    fun deviceId(context: Context, now: Long = System.currentTimeMillis()): String {
        val androidId: String = try {
            Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        } catch (_: Throwable) {
            ""
        } ?: ""

        val salt = monthlySalt(now)
        val payload = "$androidId:$salt".toByteArray(Charsets.UTF_8)
        val md = MessageDigest.getInstance("SHA-256")
        val digest = md.digest(payload)
        return digest.joinToString("") { "%02x".format(it) }
    }

    private fun monthlySalt(now: Long): String {
        val cal = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"))
        cal.timeInMillis = now
        val year = cal.get(java.util.Calendar.YEAR)
        val month = cal.get(java.util.Calendar.MONTH) + 1
        return "synora-%04d-%02d".format(year, month)
    }
}
