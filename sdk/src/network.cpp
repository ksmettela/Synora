/**
 * HTTP Network Client Implementation
 */

#include "network.hpp"

#include <chrono>
#include <cmath>
#include <ctime>
#include <iostream>
#include <sstream>

namespace acr {

// libcurl write callback
static size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

NetworkClient::NetworkClient(const std::string& server_url,
                             const std::string& api_key,
                             const std::string& device_id,
                             const DeviceInfo& device_info)
    : server_url_(server_url),
      api_key_(api_key),
      device_id_(device_id),
      device_info_(device_info) {}

NetworkClient::~NetworkClient() {
    stop(false);

    if (curl_handle_) {
        curl_easy_cleanup(curl_handle_);
        curl_handle_ = nullptr;
    }
}

bool NetworkClient::init() {
    curl_handle_ = curl_easy_init();
    if (!curl_handle_) {
        return false;
    }

    // Set common curl options
    curl_easy_setopt(curl_handle_, CURLOPT_TIMEOUT, 30L);
    curl_easy_setopt(curl_handle_, CURLOPT_CONNECTTIMEOUT, 10L);
    curl_easy_setopt(curl_handle_, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl_handle_, CURLOPT_SSL_VERIFYHOST, 2L);

    return true;
}

bool NetworkClient::start(FingerprintCache* cache, int batch_size,
                          int flush_interval) {
    if (running_) {
        return true;
    }

    cache_ = cache;
    batch_size_ = batch_size;
    flush_interval_ = flush_interval;
    stop_requested_ = false;
    retry_count_ = 0;

    running_ = true;
    transmission_thread_ = std::make_unique<std::thread>(&NetworkClient::transmission_thread_main, this);

    return true;
}

void NetworkClient::stop(bool wait_for_flush) {
    if (!running_) {
        return;
    }

    if (wait_for_flush) {
        flush();
    }

    stop_requested_ = true;
    flush_cv_.notify_all();

    if (transmission_thread_ && transmission_thread_->joinable()) {
        transmission_thread_->join();
    }

    running_ = false;
}

bool NetworkClient::flush() {
    if (!running_ || !cache_) {
        return false;
    }

    {
        std::lock_guard<std::mutex> lock(state_mutex_);
        flush_requested_ = true;
    }

    flush_cv_.notify_one();

    return true;
}

bool NetworkClient::is_running() const {
    return running_;
}

int NetworkClient::get_backoff_delay() {
    // Exponential backoff: 1, 2, 4, 8, ... 300 seconds
    int delay = 1 << retry_count_;
    if (delay > max_retry_backoff_) {
        delay = max_retry_backoff_;
    }
    return delay;
}

std::string NetworkClient::build_json_payload(
    const std::vector<FingerprintCacheEntry>& entries,
    const std::string& device_id, const DeviceInfo& device_info) {
    std::ostringstream json;

    json << "{"
         << "\"device_id\":\"" << device_id << "\","
         << "\"manufacturer\":\"" << device_info.manufacturer << "\","
         << "\"model\":\"" << device_info.model << "\","
         << "\"fingerprints\":[";

    for (size_t i = 0; i < entries.size(); ++i) {
        if (i > 0) json << ",";

        json << "{"
             << "\"timestamp_utc\":" << entries[i].timestamp_utc << ","
             << "\"fingerprint_hex\":\"";

        // Convert fingerprint to hex
        for (uint8_t byte : entries[i].fingerprint) {
            char buf[3];
            snprintf(buf, sizeof(buf), "%02x", byte);
            json << buf;
        }

        json << "\""
             << "}";
    }

    json << "]"
         << "}";

    return json.str();
}

bool NetworkClient::transmit_batch(const std::vector<FingerprintCacheEntry>& entries) {
    if (entries.empty()) {
        return true;
    }

    std::string json_payload = build_json_payload(entries, device_id_, device_info_);

    std::string response;

    // Set up curl for POST request
    std::string url = server_url_ + "/v1/fingerprints/ingest";

    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, ("X-API-Key: " + api_key_).c_str());

    curl_easy_setopt(curl_handle_, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_payload.c_str());
    curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &response);

    CURLcode res = curl_easy_perform(curl_handle_);

    long http_code = 0;
    curl_easy_getinfo(curl_handle_, CURLINFO_RESPONSE_CODE, &http_code);

    curl_slist_free_all(headers);

    if (res != CURLE_OK) {
        // Network error - retry with backoff
        return false;
    }

    if (http_code == 202) {
        // Accepted - mark as transmitted and reset retry counter
        std::vector<int> ids;
        for (const auto& entry : entries) {
            ids.push_back(entry.id);
        }
        cache_->mark_transmitted(ids);
        retry_count_ = 0;
        return true;
    } else if (http_code >= 400 && http_code < 500) {
        // Client error - don't retry
        std::cerr << "ACR: Server rejected batch (HTTP " << http_code << ")"
                  << std::endl;
        retry_count_ = 0;
        return false;
    } else if (http_code >= 500) {
        // Server error - retry with backoff
        return false;
    }

    return false;
}

void NetworkClient::transmission_thread_main() {
    while (!stop_requested_) {
        // Wait for flush request or timeout
        {
            std::unique_lock<std::mutex> lock(state_mutex_);
            bool has_flush_request = flush_requested_;
            flush_requested_ = false;

            if (!has_flush_request) {
                flush_cv_.wait_for(lock, std::chrono::seconds(flush_interval_));
            }
        }

        if (stop_requested_) {
            break;
        }

        // Try to transmit batch
        if (cache_) {
            auto entries = cache_->get_untransmitted_batch(batch_size_);

            if (!entries.empty()) {
                if (transmit_batch(entries)) {
                    retry_count_ = 0;
                } else {
                    retry_count_++;
                    int backoff = get_backoff_delay();

                    std::cerr << "ACR: Transmission failed, retrying in " << backoff
                              << " seconds" << std::endl;

                    // Sleep with check for stop
                    for (int i = 0; i < backoff && !stop_requested_; ++i) {
                        std::this_thread::sleep_for(std::chrono::seconds(1));
                    }
                }
            }
        }
    }

    // Final flush on shutdown
    if (cache_) {
        auto entries = cache_->get_untransmitted_batch(batch_size_);
        if (!entries.empty()) {
            transmit_batch(entries);
        }
    }
}

}  // namespace acr
