package io.synora.sdk.internal

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log

/**
 * Captures a single [durationMs] window of 16 kHz mono PCM from the device
 * microphone (or media playback bus on TV devices that route it through
 * MediaRecorder.AudioSource.REMOTE_SUBMIX — kept behind a flag until we have
 * OEM permission to use it).
 *
 * Synchronous by design: each call acquires AudioRecord, reads one window,
 * releases. The SDK schedules these calls on a background coroutine every
 * captureIntervalSec.
 */
internal class AudioCapturer(
    private val sampleRateHz: Int = 16_000,
    private val source: Int = MediaRecorder.AudioSource.MIC,
) {
    @SuppressLint("MissingPermission")
    fun capture(durationMs: Int): ShortArray? {
        val channelConfig = AudioFormat.CHANNEL_IN_MONO
        val encoding = AudioFormat.ENCODING_PCM_16BIT
        val minBufferBytes = AudioRecord.getMinBufferSize(sampleRateHz, channelConfig, encoding)
        if (minBufferBytes <= 0) {
            Log.w(TAG, "AudioRecord.getMinBufferSize returned $minBufferBytes")
            return null
        }

        val targetSamples = sampleRateHz * durationMs / 1000
        val record = AudioRecord(
            source,
            sampleRateHz,
            channelConfig,
            encoding,
            maxOf(minBufferBytes, targetSamples * 2),
        )
        if (record.state != AudioRecord.STATE_INITIALIZED) {
            Log.w(TAG, "AudioRecord failed to initialize")
            record.release()
            return null
        }

        val out = ShortArray(targetSamples)
        return try {
            record.startRecording()
            var offset = 0
            while (offset < targetSamples) {
                val read = record.read(out, offset, targetSamples - offset)
                if (read <= 0) {
                    Log.w(TAG, "AudioRecord.read returned $read")
                    return null
                }
                offset += read
            }
            out
        } catch (t: Throwable) {
            Log.w(TAG, "capture failed", t)
            null
        } finally {
            try {
                record.stop()
            } catch (_: IllegalStateException) {
            }
            record.release()
        }
    }

    companion object {
        private const val TAG = "SynoraAudioCapturer"
    }
}
