/**
 * SQLite-based Fingerprint Cache Implementation
 */

#include "cache.hpp"

#include <ctime>
#include <iomanip>
#include <sstream>
#include <sys/stat.h>

namespace acr {

static const char* CACHE_DIR = "/var/lib/acr";

FingerprintCache::FingerprintCache(const std::string& db_path) : db_path_(db_path) {}

FingerprintCache::~FingerprintCache() {
    if (db_) {
        sqlite3_close(db_);
        db_ = nullptr;
    }
}

bool FingerprintCache::create_schema() {
    const char* sql =
        "CREATE TABLE IF NOT EXISTS fingerprints ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  device_id TEXT NOT NULL,"
        "  fingerprint_hex TEXT NOT NULL,"
        "  timestamp_utc INTEGER NOT NULL,"
        "  transmitted BOOLEAN NOT NULL DEFAULT 0"
        ");"
        "CREATE INDEX IF NOT EXISTS idx_transmitted "
        "  ON fingerprints(transmitted, timestamp_utc);"
        "PRAGMA journal_mode = WAL;"
        "PRAGMA synchronous = NORMAL;";

    char* errmsg = nullptr;
    int rc = sqlite3_exec(db_, sql, nullptr, nullptr, &errmsg);

    if (rc != SQLITE_OK) {
        if (errmsg) {
            sqlite3_free(errmsg);
        }
        return false;
    }

    return true;
}

bool FingerprintCache::init() {
    std::lock_guard<std::mutex> lock(db_mutex_);

    // Create cache directory if needed
    mkdir(CACHE_DIR, 0755);

    // Open or create database
    int rc = sqlite3_open(db_path_.c_str(), &db_);

    if (rc != SQLITE_OK) {
        if (db_) {
            sqlite3_close(db_);
            db_ = nullptr;
        }
        return false;
    }

    // Create schema
    if (!create_schema()) {
        sqlite3_close(db_);
        db_ = nullptr;
        return false;
    }

    return true;
}

std::string FingerprintCache::fingerprint_to_hex(const Fingerprint& fp) {
    std::ostringstream oss;
    for (uint8_t byte : fp) {
        oss << std::hex << std::setfill('0') << std::setw(2) << (int)byte;
    }
    return oss.str();
}

bool FingerprintCache::hex_to_fingerprint(const std::string& hex, Fingerprint& fp) {
    if (hex.length() != 64) {
        return false;
    }

    for (size_t i = 0; i < 32; ++i) {
        std::string byte_str = hex.substr(i * 2, 2);
        try {
            fp[i] = static_cast<uint8_t>(std::stoi(byte_str, nullptr, 16));
        } catch (...) {
            return false;
        }
    }

    return true;
}

bool FingerprintCache::insert(const std::string& device_id,
                              const Fingerprint& fingerprint, int64_t timestamp_utc) {
    if (!db_) {
        return false;
    }

    std::lock_guard<std::mutex> lock(db_mutex_);

    std::string fp_hex = fingerprint_to_hex(fingerprint);

    std::string sql = "INSERT INTO fingerprints (device_id, fingerprint_hex, timestamp_utc) "
                      "VALUES (?, ?, ?)";

    sqlite3_stmt* stmt = nullptr;
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        return false;
    }

    sqlite3_bind_text(stmt, 1, device_id.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, fp_hex.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_int64(stmt, 3, timestamp_utc);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return rc == SQLITE_DONE;
}

std::vector<FingerprintCacheEntry> FingerprintCache::get_untransmitted_batch(int limit) {
    std::vector<FingerprintCacheEntry> entries;

    if (!db_) {
        return entries;
    }

    std::lock_guard<std::mutex> lock(db_mutex_);

    std::string sql =
        "SELECT id, device_id, fingerprint_hex, timestamp_utc "
        "FROM fingerprints WHERE transmitted = 0 "
        "ORDER BY timestamp_utc ASC LIMIT ?";

    sqlite3_stmt* stmt = nullptr;
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        return entries;
    }

    sqlite3_bind_int(stmt, 1, limit);

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        FingerprintCacheEntry entry;
        entry.id = sqlite3_column_int(stmt, 0);
        entry.device_id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        entry.timestamp_utc = sqlite3_column_int64(stmt, 3);
        entry.transmitted = false;

        std::string hex_str =
            reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));

        if (hex_to_fingerprint(hex_str, entry.fingerprint)) {
            entries.push_back(entry);
        }
    }

    sqlite3_finalize(stmt);

    return entries;
}

bool FingerprintCache::mark_transmitted(const std::vector<int>& ids) {
    if (!db_ || ids.empty()) {
        return true;
    }

    std::lock_guard<std::mutex> lock(db_mutex_);

    // Build placeholder list
    std::string placeholders;
    for (size_t i = 0; i < ids.size(); ++i) {
        if (i > 0) placeholders += ",";
        placeholders += "?";
    }

    std::string sql = "UPDATE fingerprints SET transmitted = 1 WHERE id IN (" +
                      placeholders + ")";

    sqlite3_stmt* stmt = nullptr;
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        return false;
    }

    for (size_t i = 0; i < ids.size(); ++i) {
        sqlite3_bind_int(stmt, i + 1, ids[i]);
    }

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return rc == SQLITE_DONE;
}

int FingerprintCache::get_count() {
    if (!db_) {
        return 0;
    }

    std::lock_guard<std::mutex> lock(db_mutex_);

    const char* sql = "SELECT COUNT(*) FROM fingerprints";
    sqlite3_stmt* stmt = nullptr;
    int rc = sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        return 0;
    }

    int count = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        count = sqlite3_column_int(stmt, 0);
    }

    sqlite3_finalize(stmt);

    return count;
}

bool FingerprintCache::purge_all() {
    if (!db_) {
        return false;
    }

    std::lock_guard<std::mutex> lock(db_mutex_);

    const char* sql = "DELETE FROM fingerprints";
    char* errmsg = nullptr;
    int rc = sqlite3_exec(db_, sql, nullptr, nullptr, &errmsg);

    if (rc != SQLITE_OK) {
        if (errmsg) {
            sqlite3_free(errmsg);
        }
        return false;
    }

    return true;
}

bool FingerprintCache::purge_old(int days_old) {
    if (!db_) {
        return false;
    }

    std::lock_guard<std::mutex> lock(db_mutex_);

    int64_t cutoff_timestamp = std::time(nullptr) - (days_old * 86400);

    std::string sql = "DELETE FROM fingerprints WHERE timestamp_utc < ?";

    sqlite3_stmt* stmt = nullptr;
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        return false;
    }

    sqlite3_bind_int64(stmt, 1, cutoff_timestamp);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return rc == SQLITE_DONE;
}

}  // namespace acr
