/**
 * HTTP Network Client for Batch Fingerprint Transmission
 *
 * Handles transmission to Synora ingest server with exponential backoff.
 */

#ifndef ACR_NETWORK_HPP
#define ACR_NETWORK_HPP

#include "cache.hpp"

#include <atomic>
#include <condition_variable>
#include <curl/curl.h>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

namespace acr {

/**
 * Device info for transmission
 */
struct DeviceInfo {
    std::string manufacturer;
    std::string model;
};

/**
 * Network Transmission Client
 *
 * Transmits fingerprint batches to server with automatic retry.
 */
class NetworkClient {
public:
    /**
     * Constructor
     *
     * @param server_url Base URL of ingest server
     * @param api_key API key for authentication
     * @param device_id Device identifier
     * @param device_info Device manufacturer and model
     */
    NetworkClient(const std::string& server_url, const std::string& api_key,
                  const std::string& device_id, const DeviceInfo& device_info);

    ~NetworkClient();

    /**
     * Initialize network client
     *
     * @return true if successful
     */
    bool init();

    /**
     * Start background transmission thread
     *
     * @param cache Fingerprint cache to read from
     * @param batch_size Number of fingerprints per batch
     * @param flush_interval Seconds between flush attempts
     * @return true if successful
     */
    bool start(FingerprintCache* cache, int batch_size, int flush_interval);

    /**
     * Stop background transmission thread
     *
     * @param wait_for_flush If true, flush remaining items before stopping
     */
    void stop(bool wait_for_flush = true);

    /**
     * Force immediate transmission of cached fingerprints
     *
     * @return true if successful
     */
    bool flush();

    /**
     * Check if transmission thread is running
     *
     * @return true if running
     */
    bool is_running() const;

private:
    std::string server_url_;
    std::string api_key_;
    std::string device_id_;
    DeviceInfo device_info_;

    CURL* curl_handle_ = nullptr;
    FingerprintCache* cache_ = nullptr;

    std::atomic<bool> running_{false};
    std::atomic<bool> stop_requested_{false};
    std::unique_ptr<std::thread> transmission_thread_;

    std::mutex state_mutex_;
    std::condition_variable flush_cv_;
    bool flush_requested_ = false;

    int batch_size_ = 20;
    int flush_interval_ = 60;
    int retry_count_ = 0;
    int max_retry_backoff_ = 300;  // 5 minutes

    /**
     * Background transmission thread main loop
     */
    void transmission_thread_main();

    /**
     * Get backoff delay for retry attempt
     *
     * @return Delay in seconds
     */
    int get_backoff_delay();

    /**
     * Transmit a batch of fingerprints
     *
     * @param entries Fingerprints to transmit
     * @return true if successful (202 Accepted)
     */
    bool transmit_batch(const std::vector<FingerprintCacheEntry>& entries);

    /**
     * Build JSON payload for transmission
     *
     * @param entries Fingerprints to encode
     * @return JSON string
     */
    static std::string build_json_payload(
        const std::vector<FingerprintCacheEntry>& entries,
        const std::string& device_id, const DeviceInfo& device_info);
};

}  // namespace acr

#endif /* ACR_NETWORK_HPP */
