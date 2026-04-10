/**
 * Synora SDK Test Program
 *
 * Simple test that demonstrates SDK initialization and usage.
 */

#include "../include/acr.h"

#include <iostream>
#include <thread>
#include <unistd.h>

int main() {
    std::cout << "Synora SDK Test Program v" << acr_version() << std::endl;
    std::cout << "================================" << std::endl;

    // Configuration
    acr_config_t config{
        .server_url = "http://localhost:8080",
        .api_key = "test_api_key_123",
        .batch_size = 10,
        .flush_interval_sec = 5,
        .sample_rate_hz = 16000,
        .capture_duration_ms = 3000,
        .capture_interval_sec = 10,
    };

    // Initialize SDK
    std::cout << "\n1. Initializing ACR SDK..." << std::endl;
    acr_error_t err = acr_init(&config);
    if (err != ACR_SUCCESS) {
        std::cerr << "ERROR: Failed to initialize SDK (error code: " << err << ")"
                  << std::endl;
        return 1;
    }
    std::cout << "   OK: SDK initialized" << std::endl;

    // Get device ID
    std::cout << "\n2. Getting device ID..." << std::endl;
    char device_id[256];
    err = acr_get_device_id(device_id, sizeof(device_id));
    if (err != ACR_SUCCESS) {
        std::cerr << "ERROR: Failed to get device ID (error code: " << err << ")"
                  << std::endl;
        return 1;
    }
    std::cout << "   Device ID: " << device_id << std::endl;

    // Set consent
    std::cout << "\n3. Setting user consent to opted-in..." << std::endl;
    err = acr_set_consent(true);
    if (err != ACR_SUCCESS) {
        std::cerr << "ERROR: Failed to set consent (error code: " << err << ")"
                  << std::endl;
        return 1;
    }
    std::cout << "   OK: Consent set to opted-in" << std::endl;

    // Start capture
    std::cout << "\n4. Starting ACR capture and transmission..." << std::endl;
    err = acr_start();
    if (err != ACR_SUCCESS) {
        std::cerr << "ERROR: Failed to start capture (error code: " << err << ")"
                  << std::endl;
        return 1;
    }
    std::cout << "   OK: Capture started" << std::endl;

    // Let it run for 10 seconds
    std::cout << "\n5. Running capture for 10 seconds..." << std::endl;
    for (int i = 0; i < 10; ++i) {
        std::cout << "   " << (i + 1) << "/10 seconds..." << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    // Flush
    std::cout << "\n6. Flushing cached fingerprints..." << std::endl;
    err = acr_flush();
    if (err != ACR_SUCCESS) {
        std::cerr << "WARNING: Flush returned error code: " << err << std::endl;
    } else {
        std::cout << "   OK: Flush initiated" << std::endl;
    }

    // Stop
    std::cout << "\n7. Stopping ACR..." << std::endl;
    err = acr_stop();
    if (err != ACR_SUCCESS) {
        std::cerr << "ERROR: Failed to stop (error code: " << err << ")" << std::endl;
        return 1;
    }
    std::cout << "   OK: ACR stopped" << std::endl;

    std::cout << "\n================================" << std::endl;
    std::cout << "Test completed successfully!" << std::endl;

    return 0;
}
