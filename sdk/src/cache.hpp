/**
 * SQLite-based Fingerprint Cache
 *
 * Stores fingerprints locally for batch transmission.
 */

#ifndef ACR_CACHE_HPP
#define ACR_CACHE_HPP

#include "fingerprint.hpp"

#include <cstdint>
#include <mutex>
#include <sqlite3.h>
#include <string>
#include <vector>

namespace acr {

/**
 * Cached Fingerprint Entry
 */
struct FingerprintCacheEntry {
    int id;
    std::string device_id;
    Fingerprint fingerprint;
    int64_t timestamp_utc;
    bool transmitted;
};

/**
 * Fingerprint Cache Manager
 *
 * SQLite-backed cache with thread-safe access.
 */
class FingerprintCache {
public:
    /**
     * Constructor
     *
     * @param db_path Path to SQLite database file (default: /var/lib/acr/fingerprint_cache.db)
     */
    explicit FingerprintCache(
        const std::string& db_path = "/var/lib/acr/fingerprint_cache.db");

    ~FingerprintCache();

    /**
     * Initialize cache (creates database if needed)
     *
     * @return true if successful
     */
    bool init();

    /**
     * Insert a fingerprint into cache
     *
     * @param device_id Device identifier
     * @param fingerprint Fingerprint hash
     * @param timestamp_utc UTC timestamp in seconds
     * @return true if successful
     */
    bool insert(const std::string& device_id, const Fingerprint& fingerprint,
                int64_t timestamp_utc);

    /**
     * Get untransmitted fingerprints (oldest first)
     *
     * @param limit Maximum number of entries to retrieve
     * @return Vector of cache entries
     */
    std::vector<FingerprintCacheEntry> get_untransmitted_batch(int limit);

    /**
     * Mark fingerprints as transmitted
     *
     * @param ids Database IDs to mark as transmitted
     * @return true if successful
     */
    bool mark_transmitted(const std::vector<int>& ids);

    /**
     * Get total number of cached fingerprints
     *
     * @return Count of entries
     */
    int get_count();

    /**
     * Delete all cached fingerprints
     *
     * @return true if successful
     */
    bool purge_all();

    /**
     * Delete old entries (older than N days)
     *
     * @param days_old Number of days to keep
     * @return true if successful
     */
    bool purge_old(int days_old = 7);

private:
    std::string db_path_;
    sqlite3* db_ = nullptr;
    std::mutex db_mutex_;

    bool create_schema();

    /**
     * Convert fingerprint to hex string
     */
    static std::string fingerprint_to_hex(const Fingerprint& fp);

    /**
     * Convert hex string to fingerprint
     */
    static bool hex_to_fingerprint(const std::string& hex, Fingerprint& fp);
};

}  // namespace acr

#endif /* ACR_CACHE_HPP */
