/**
 * ACRaaS SDK Main Library Implementation
 */

#include "../include/acr.h"
#include "audio_capture.hpp"
#include "cache.hpp"
#include "consent.hpp"
#include "device_id.hpp"
#include "fingerprint.hpp"
#include "network.hpp"

#include <ctime>
#include <iostream>
#include <memory>
#include <mutex>

namespace acr {

/**
 * Global ACR SDK State
 */
class AcrSdkState {
public:
    enum State {
        UNINITIALIZED,
        INITIALIZED,
        RUNNING,
        STOPPED,
    };

    State state = UNINITIALIZED;
    std::mutex state_mutex;

    std::unique_ptr<DeviceIdManager> device_id_manager;
    std::unique_ptr<FingerprintCache> cache;
    std::unique_ptr<FingerprintEngine> fingerprint_engine;
    std::unique_ptr<AudioCapture> audio_capture;
    std::unique_ptr<NetworkClient> network_client;
    std::unique_ptr<ConsentManager> consent_manager;

    acr_config_t config{};
    std::string device_id;
};

}  // namespace acr

// Global SDK state
static std::unique_ptr<acr::AcrSdkState> g_acr_state;

extern "C" {

acr_error_t acr_init(const acr_config_t* config) {
    if (!config || !config->server_url || !config->api_key) {
        return ACR_ERROR_INIT;
    }

    if (g_acr_state) {
        return ACR_SUCCESS;  // Already initialized
    }

    try {
        g_acr_state = std::make_unique<acr::AcrSdkState>();

        // Copy config
        g_acr_state->config = *config;

        // Initialize managers
        g_acr_state->device_id_manager = std::make_unique<acr::DeviceIdManager>();
        g_acr_state->device_id = g_acr_state->device_id_manager->get_device_id();

        if (g_acr_state->device_id.empty()) {
            g_acr_state.reset();
            return ACR_ERROR_INIT;
        }

        // Initialize cache
        g_acr_state->cache = std::make_unique<acr::FingerprintCache>();
        if (!g_acr_state->cache->init()) {
            g_acr_state.reset();
            return ACR_ERROR_INIT;
        }

        // Initialize fingerprinting engine
        int sample_rate = config->sample_rate_hz > 0 ? config->sample_rate_hz : 16000;
        g_acr_state->fingerprint_engine =
            std::make_unique<acr::FingerprintEngine>(sample_rate);

        // Initialize consent manager
        g_acr_state->consent_manager = std::make_unique<acr::ConsentManager>();

        // Initialize network client
        acr::DeviceInfo device_info{
            .manufacturer = "Unknown",
            .model = "Unknown",
        };
        g_acr_state->network_client = std::make_unique<acr::NetworkClient>(
            config->server_url, config->api_key, g_acr_state->device_id,
            device_info);
        if (!g_acr_state->network_client->init()) {
            g_acr_state.reset();
            return ACR_ERROR_NETWORK;
        }

        // Initialize audio capture
        int capture_duration = config->capture_duration_ms > 0
                                   ? config->capture_duration_ms
                                   : 3000;
        int capture_interval =
            config->capture_interval_sec > 0 ? config->capture_interval_sec : 30;

        g_acr_state->audio_capture = std::make_unique<acr::AudioCapture>(
            sample_rate, capture_duration, capture_interval);

        // Set up audio capture callback
        auto fingerprint_callback = [](const int16_t* samples, size_t num_samples) {
            if (!g_acr_state) return;

            // Fingerprint the audio
            auto fp = g_acr_state->fingerprint_engine->fingerprint(samples, num_samples);

            // Cache the fingerprint
            int64_t timestamp = std::time(nullptr);
            g_acr_state->cache->insert(g_acr_state->device_id, fp, timestamp);
        };

        if (!g_acr_state->audio_capture->init(fingerprint_callback)) {
            g_acr_state.reset();
            return ACR_ERROR_AUDIO;
        }

        g_acr_state->state = acr::AcrSdkState::INITIALIZED;

        return ACR_SUCCESS;

    } catch (const std::exception& e) {
        std::cerr << "ACR: Initialization failed: " << e.what() << std::endl;
        g_acr_state.reset();
        return ACR_ERROR_INIT;
    }
}

acr_error_t acr_start(void) {
    if (!g_acr_state) {
        return ACR_ERROR_INIT;
    }

    std::lock_guard<std::mutex> lock(g_acr_state->state_mutex);

    // Check consent
    if (!g_acr_state->consent_manager->is_opted_in()) {
        return ACR_ERROR_CONSENT;
    }

    if (g_acr_state->state == acr::AcrSdkState::RUNNING) {
        return ACR_SUCCESS;
    }

    try {
        // Start audio capture
        if (!g_acr_state->audio_capture->start()) {
            return ACR_ERROR_AUDIO;
        }

        // Start network transmission thread
        int batch_size = g_acr_state->config.batch_size > 0
                             ? g_acr_state->config.batch_size
                             : 20;
        int flush_interval = g_acr_state->config.flush_interval_sec > 0
                                 ? g_acr_state->config.flush_interval_sec
                                 : 60;

        if (!g_acr_state->network_client->start(g_acr_state->cache.get(), batch_size,
                                                 flush_interval)) {
            g_acr_state->audio_capture->stop();
            return ACR_ERROR_NETWORK;
        }

        g_acr_state->state = acr::AcrSdkState::RUNNING;

        return ACR_SUCCESS;

    } catch (const std::exception& e) {
        std::cerr << "ACR: Start failed: " << e.what() << std::endl;
        return ACR_ERROR_INIT;
    }
}

acr_error_t acr_stop(void) {
    if (!g_acr_state) {
        return ACR_ERROR_INIT;
    }

    std::lock_guard<std::mutex> lock(g_acr_state->state_mutex);

    if (g_acr_state->state != acr::AcrSdkState::RUNNING) {
        return ACR_SUCCESS;
    }

    try {
        // Stop audio capture
        if (g_acr_state->audio_capture) {
            g_acr_state->audio_capture->stop();
        }

        // Stop network transmission (with final flush)
        if (g_acr_state->network_client) {
            g_acr_state->network_client->stop(true);
        }

        g_acr_state->state = acr::AcrSdkState::STOPPED;

        return ACR_SUCCESS;

    } catch (const std::exception& e) {
        std::cerr << "ACR: Stop failed: " << e.what() << std::endl;
        return ACR_ERROR_INIT;
    }
}

acr_error_t acr_set_consent(bool opted_in) {
    if (!g_acr_state) {
        return ACR_ERROR_INIT;
    }

    try {
        if (!g_acr_state->consent_manager->set_consent(opted_in)) {
            return ACR_ERROR_INIT;
        }

        // If opting out, stop capture and purge cache
        if (!opted_in) {
            if (g_acr_state->state == acr::AcrSdkState::RUNNING) {
                g_acr_state->audio_capture->stop();
                g_acr_state->network_client->stop(false);
            }
            g_acr_state->cache->purge_all();
        }

        return ACR_SUCCESS;

    } catch (const std::exception& e) {
        std::cerr << "ACR: Consent update failed: " << e.what() << std::endl;
        return ACR_ERROR_INIT;
    }
}

acr_error_t acr_flush(void) {
    if (!g_acr_state || !g_acr_state->network_client) {
        return ACR_ERROR_INIT;
    }

    try {
        if (!g_acr_state->network_client->flush()) {
            return ACR_ERROR_NETWORK;
        }

        return ACR_SUCCESS;

    } catch (const std::exception& e) {
        std::cerr << "ACR: Flush failed: " << e.what() << std::endl;
        return ACR_ERROR_NETWORK;
    }
}

acr_error_t acr_get_device_id(char* buf, size_t len) {
    if (!buf || len == 0) {
        return ACR_ERROR_INIT;
    }

    if (!g_acr_state || g_acr_state->device_id.empty()) {
        return ACR_ERROR_INIT;
    }

    if (g_acr_state->device_id.length() >= len) {
        return ACR_ERROR_INIT;
    }

    std::copy(g_acr_state->device_id.begin(), g_acr_state->device_id.end(), buf);
    buf[g_acr_state->device_id.length()] = '\0';

    return ACR_SUCCESS;
}

const char* acr_version(void) {
    return ACR_SDK_VERSION;
}

}  // extern "C"
