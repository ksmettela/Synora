package io.synora.sdk.internal

/**
 * JNI bridge to the shared C++ fingerprint algorithm. Same algorithm runs on
 * the server side (via fingerprint_cli) so hashes compare byte-for-byte.
 */
internal object NativeFingerprint {
    init {
        System.loadLibrary("synora_sdk")
    }

    /**
     * Compute a 256-bit (32-byte) Haitsma-Kalker fingerprint over [pcm].
     *
     * @param pcm mono 16-bit PCM. At least 4096 samples; longer windows
     *            improve robustness.
     * @param sampleRate sample rate of [pcm] in Hz. Typically 16000.
     * @return 32-byte fingerprint, or null on invalid input.
     */
    @JvmStatic
    external fun fingerprint(pcm: ShortArray, sampleRate: Int): ByteArray?
}
