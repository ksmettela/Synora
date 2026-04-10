/**
 * Persistent Consent Management
 *
 * Manages user consent status with file-based persistence.
 */

#ifndef ACR_CONSENT_HPP
#define ACR_CONSENT_HPP

#include <mutex>
#include <string>

namespace acr {

/**
 * Consent Manager
 *
 * Handles user consent with persistent storage.
 */
class ConsentManager {
public:
    /**
     * Constructor
     *
     * @param consent_file Path to consent file (default: /var/lib/acr/consent)
     */
    explicit ConsentManager(const std::string& consent_file = "/var/lib/acr/consent");

    /**
     * Get current consent status
     *
     * @return true if user has opted in, false otherwise
     */
    bool is_opted_in();

    /**
     * Set user consent
     *
     * When set to false, clears all pending operations.
     *
     * @param opted_in true to enable ACR, false to disable
     * @return true if successful
     */
    bool set_consent(bool opted_in);

    /**
     * Load consent status from persistent storage
     *
     * @return true if opted in, false otherwise
     */
    bool load_consent();

private:
    std::string consent_file_;
    bool opted_in_ = false;
    bool cached_ = false;
    std::mutex consent_mutex_;

    /**
     * Save consent status to file
     *
     * @param opted_in Consent status
     * @return true if successful
     */
    bool save_consent(bool opted_in);

    /**
     * Check if consent file exists and contains "opted_out"
     *
     * @return true if opted out file exists
     */
    bool check_opted_out_file();
};

}  // namespace acr

#endif /* ACR_CONSENT_HPP */
