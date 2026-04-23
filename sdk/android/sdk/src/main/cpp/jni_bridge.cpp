// Minimal JNI bridge: expose the shared C++ fingerprint algorithm to Kotlin.
//
// On Android we do not use the full device SDK (ALSA/libcurl/SQLite are not
// available or not idiomatic); instead Kotlin owns audio capture
// (AudioRecord), local cache (Room/SQLite), network (OkHttp), and consent
// (SharedPreferences). The native side is only responsible for the one thing
// that must be shared with the desktop SDK to keep fingerprints compatible:
// the FFT + Haitsma-Kalker hash.

#include <jni.h>
#include <cstdint>
#include <vector>

#include "fingerprint.hpp"

extern "C"
JNIEXPORT jbyteArray JNICALL
Java_io_synora_sdk_internal_NativeFingerprint_fingerprint(
        JNIEnv* env,
        jclass /*clazz*/,
        jshortArray pcm,
        jint sampleRate) {
    if (pcm == nullptr) return nullptr;

    const jsize num_samples = env->GetArrayLength(pcm);
    if (num_samples < 4096) return nullptr;

    std::vector<int16_t> buf(static_cast<size_t>(num_samples));
    env->GetShortArrayRegion(pcm, 0, num_samples, buf.data());

    try {
        acr::FingerprintEngine engine(sampleRate, 4096);
        auto fp = engine.fingerprint(buf.data(), buf.size());
        jbyteArray out = env->NewByteArray(static_cast<jsize>(fp.size()));
        if (out == nullptr) return nullptr;
        env->SetByteArrayRegion(out, 0, static_cast<jsize>(fp.size()),
                                reinterpret_cast<const jbyte*>(fp.data()));
        return out;
    } catch (...) {
        return nullptr;
    }
}
