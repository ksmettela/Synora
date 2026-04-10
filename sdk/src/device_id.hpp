/**
 * Stable Device ID Generation
 *
 * Generates a stable device identifier based on MAC address,
 * manufacturer, and model information.
 */

#ifndef ACR_DEVICE_ID_HPP
#define ACR_DEVICE_ID_HPP

#include <string>

namespace acr {

/**
 * Device ID Manager
 *
 * Generates and caches stable device IDs.
 */
class DeviceIdManager {
public:
    /**
     * Get or generate the device ID
     *
     * @return Hex-encoded SHA256 device ID
     */
    std::string get_device_id();

    /**
     * Force regenerate the device ID (useful for testing)
     *
     * @return Hex-encoded SHA256 device ID
     */
    std::string regenerate_device_id();

private:
    std::string cached_device_id_;
    bool cache_loaded_ = false;

    /**
     * Read MAC address from network interface
     *
     * @return MAC address string or empty if not found
     */
    static std::string read_mac_address();

    /**
     * Read manufacturer and model from OS
     *
     * @return "manufacturer|model" string
     */
    static std::string read_device_info();

    /**
     * Load device ID from cache file
     *
     * @return Cached device ID or empty if not found
     */
    static std::string load_from_cache();

    /**
     * Save device ID to cache file
     *
     * @param device_id ID to cache
     * @return true if successful
     */
    static bool save_to_cache(const std::string& device_id);

    /**
     * Generate device ID from components
     *
     * @param mac_address MAC address
     * @param device_info "manufacturer|model" string
     * @return Hex-encoded SHA256 hash
     */
    static std::string generate_device_id(const std::string& mac_address,
                                          const std::string& device_info);
};

}  // namespace acr

#endif /* ACR_DEVICE_ID_HPP */
