/**
 * Stable Device ID Generation Implementation
 */

#include "device_id.hpp"

#include <fstream>
#include <iomanip>
#include <iostream>
#include <openssl/evp.h>
#include <openssl/sha.h>
#include <sstream>
#include <sys/stat.h>

namespace acr {

static const char* DEVICE_ID_SALT = "Synora_v1_device_salt_2024";
static const char* CACHE_DIR = "/var/lib/acr";
static const char* CACHE_FILE = "/var/lib/acr/device_id";

std::string DeviceIdManager::read_mac_address() {
    // Try common network interface paths
    const char* interfaces[] = {"eth0", "wlan0", "eth1", "wlan1"};

    for (const auto& iface : interfaces) {
        std::string path = std::string("/sys/class/net/") + iface + "/address";
        std::ifstream file(path);

        if (file.is_open()) {
            std::string mac;
            if (std::getline(file, mac)) {
                // Remove trailing whitespace
                mac.erase(mac.find_last_not_of(" \n\r\t") + 1);
                if (!mac.empty()) {
                    return mac;
                }
            }
        }
    }

    // Fallback: generate from /proc/net/arp
    std::ifstream arp_file("/proc/net/arp");
    if (arp_file.is_open()) {
        std::string line;
        while (std::getline(arp_file, line)) {
            // Parse ARP table for first entry with MAC
            std::istringstream iss(line);
            std::string ip, hw_type, flags, mac;
            iss >> ip >> hw_type >> flags >> mac;

            if (!mac.empty() && mac != "00:00:00:00:00:00") {
                return mac;
            }
        }
    }

    return "";
}

std::string DeviceIdManager::read_device_info() {
    std::string manufacturer = "Unknown";
    std::string model = "Unknown";

    // Try /etc/os-release
    std::ifstream os_release("/etc/os-release");
    if (os_release.is_open()) {
        std::string line;
        while (std::getline(os_release, line)) {
            if (line.find("NAME=") == 0) {
                manufacturer = line.substr(5);
                // Remove quotes if present
                if (manufacturer.front() == '"') manufacturer = manufacturer.substr(1);
                if (manufacturer.back() == '"') manufacturer.pop_back();
            }
            if (line.find("VERSION=") == 0) {
                model = line.substr(8);
                if (model.front() == '"') model = model.substr(1);
                if (model.back() == '"') model.pop_back();
            }
        }
    }

    // Try /etc/device-id if available (TV OS specific)
    std::ifstream device_file("/etc/device-id");
    if (device_file.is_open()) {
        std::string line;
        while (std::getline(device_file, line)) {
            if (line.find("model=") == 0) {
                model = line.substr(6);
            }
            if (line.find("manufacturer=") == 0) {
                manufacturer = line.substr(13);
            }
        }
    }

    return manufacturer + "|" + model;
}

std::string DeviceIdManager::load_from_cache() {
    std::ifstream cache(CACHE_FILE);
    if (cache.is_open()) {
        std::string device_id;
        if (std::getline(cache, device_id) && !device_id.empty()) {
            return device_id;
        }
    }
    return "";
}

bool DeviceIdManager::save_to_cache(const std::string& device_id) {
    // Create cache directory if it doesn't exist
    mkdir(CACHE_DIR, 0755);

    std::ofstream cache(CACHE_FILE);
    if (!cache.is_open()) {
        return false;
    }

    cache << device_id << std::endl;
    cache.close();

    // Set restrictive permissions
    chmod(CACHE_FILE, 0600);

    return true;
}

std::string DeviceIdManager::generate_device_id(const std::string& mac_address,
                                                const std::string& device_info) {
    // Construct input: MAC|manufacturer|model|SALT
    std::string input = mac_address + "|" + device_info + "|" + DEVICE_ID_SALT;

    // Compute SHA256
    EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
    if (!mdctx) {
        return "";
    }

    unsigned char hash[EVP_MAX_MD_SIZE];
    unsigned int hash_len = 0;

    if (!EVP_DigestInit_ex(mdctx, EVP_sha256(), nullptr) ||
        !EVP_DigestUpdate(mdctx, input.c_str(), input.length()) ||
        !EVP_DigestFinal_ex(mdctx, hash, &hash_len)) {
        EVP_MD_CTX_free(mdctx);
        return "";
    }

    EVP_MD_CTX_free(mdctx);

    // Convert to hex string
    std::ostringstream oss;
    for (unsigned int i = 0; i < hash_len; ++i) {
        oss << std::hex << std::setfill('0') << std::setw(2)
            << (int)hash[i];
    }

    return oss.str();
}

std::string DeviceIdManager::get_device_id() {
    if (cache_loaded_) {
        return cached_device_id_;
    }

    // Try to load from cache
    cached_device_id_ = load_from_cache();
    if (!cached_device_id_.empty()) {
        cache_loaded_ = true;
        return cached_device_id_;
    }

    // Generate new device ID
    return regenerate_device_id();
}

std::string DeviceIdManager::regenerate_device_id() {
    std::string mac = read_mac_address();
    if (mac.empty()) {
        mac = "unknown";
    }

    std::string device_info = read_device_info();

    std::string device_id = generate_device_id(mac, device_info);

    if (!device_id.empty()) {
        save_to_cache(device_id);
        cached_device_id_ = device_id;
        cache_loaded_ = true;
    }

    return device_id;
}

}  // namespace acr
