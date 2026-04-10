/**
 * Synora SDK - JNI Bridge Implementation
 *
 * Implements JNI bindings for Kotlin/Java to call native C SDK.
 */

#include <jni.h>
#include <string>

#include "../include/acr.h"

// Helper to convert C string to Java string
static jstring CStringToJavaString(JNIEnv* env, const char* str) {
    if (!str) {
        return env->NewStringUTF("");
    }
    return env->NewStringUTF(str);
}

// Helper to convert Java string to C string
static std::string JavaStringToCString(JNIEnv* env, jstring str) {
    if (!str) {
        return "";
    }
    const char* c_str = env->GetStringUTFChars(str, nullptr);
    std::string result(c_str);
    env->ReleaseStringUTFChars(str, c_str);
    return result;
}

extern "C" {

/**
 * JNI: Initialize Synora SDK
 *
 * Java signature:
 * private external fun native_init(
 *     serverUrl: String,
 *     apiKey: String,
 *     batchSize: Int,
 *     flushIntervalSec: Int,
 *     sampleRateHz: Int,
 *     captureDurationMs: Int,
 *     captureIntervalSec: Int
 * ): Int
 */
JNIEXPORT jint JNICALL Java_io_acraas_sdk_AcrSdk_native_1init(
    JNIEnv* env, jclass clazz,
    jstring serverUrl, jstring apiKey,
    jint batchSize, jint flushIntervalSec,
    jint sampleRateHz, jint captureDurationMs,
    jint captureIntervalSec) {

    std::string server_url = JavaStringToCString(env, serverUrl);
    std::string api_key = JavaStringToCString(env, apiKey);

    acr_config_t config{
        .server_url = server_url.c_str(),
        .api_key = api_key.c_str(),
        .batch_size = static_cast<int>(batchSize),
        .flush_interval_sec = static_cast<int>(flushIntervalSec),
        .sample_rate_hz = static_cast<int>(sampleRateHz),
        .capture_duration_ms = static_cast<int>(captureDurationMs),
        .capture_interval_sec = static_cast<int>(captureIntervalSec),
    };

    return static_cast<jint>(acr_init(&config));
}

/**
 * JNI: Start ACR capture
 *
 * Java signature:
 * private external fun native_start(): Int
 */
JNIEXPORT jint JNICALL Java_io_acraas_sdk_AcrSdk_native_1start(
    JNIEnv* env, jclass clazz) {
    return static_cast<jint>(acr_start());
}

/**
 * JNI: Stop ACR capture
 *
 * Java signature:
 * private external fun native_stop(): Int
 */
JNIEXPORT jint JNICALL Java_io_acraas_sdk_AcrSdk_native_1stop(
    JNIEnv* env, jclass clazz) {
    return static_cast<jint>(acr_stop());
}

/**
 * JNI: Set user consent
 *
 * Java signature:
 * private external fun native_set_consent(optedIn: Boolean): Int
 */
JNIEXPORT jint JNICALL Java_io_acraas_sdk_AcrSdk_native_1set_1consent(
    JNIEnv* env, jclass clazz,
    jboolean optedIn) {
    return static_cast<jint>(acr_set_consent(optedIn == JNI_TRUE));
}

/**
 * JNI: Flush cached fingerprints
 *
 * Java signature:
 * private external fun native_flush(): Int
 */
JNIEXPORT jint JNICALL Java_io_acraas_sdk_AcrSdk_native_1flush(
    JNIEnv* env, jclass clazz) {
    return static_cast<jint>(acr_flush());
}

/**
 * JNI: Get device ID
 *
 * Java signature:
 * private external fun native_get_device_id(): String
 */
JNIEXPORT jstring JNICALL Java_io_acraas_sdk_AcrSdk_native_1get_1device_1id(
    JNIEnv* env, jclass clazz) {
    char device_id[256];
    acr_error_t err = acr_get_device_id(device_id, sizeof(device_id));

    if (err != ACR_SUCCESS) {
        return CStringToJavaString(env, "");
    }

    return CStringToJavaString(env, device_id);
}

/**
 * JNI: Get SDK version
 *
 * Java signature:
 * private external fun native_version(): String
 */
JNIEXPORT jstring JNICALL Java_io_acraas_sdk_AcrSdk_native_1version(
    JNIEnv* env, jclass clazz) {
    const char* version = acr_version();
    return CStringToJavaString(env, version);
}

}  // extern "C"
