/**
 * Persistent Consent Management Implementation
 */

#include "consent.hpp"

#include <fstream>
#include <sys/stat.h>

namespace acr {

static const char* CONSENT_DIR = "/var/lib/acr";

ConsentManager::ConsentManager(const std::string& consent_file)
    : consent_file_(consent_file) {
    load_consent();
}

bool ConsentManager::check_opted_out_file() {
    std::ifstream file(consent_file_);
    if (file.is_open()) {
        std::string content;
        if (std::getline(file, content)) {
            return content == "opted_out";
        }
    }
    return false;
}

bool ConsentManager::load_consent() {
    std::lock_guard<std::mutex> lock(consent_mutex_);

    // Check for opted_out file
    opted_in_ = !check_opted_out_file();
    cached_ = true;

    return true;
}

bool ConsentManager::is_opted_in() {
    std::lock_guard<std::mutex> lock(consent_mutex_);
    return opted_in_;
}

bool ConsentManager::save_consent(bool opted_in) {
    // Create directory if needed
    mkdir(CONSENT_DIR, 0755);

    std::ofstream file(consent_file_);
    if (!file.is_open()) {
        return false;
    }

    if (opted_in) {
        file << "opted_in" << std::endl;
    } else {
        file << "opted_out" << std::endl;
    }

    file.close();

    // Set restrictive permissions
    chmod(consent_file_.c_str(), 0644);

    return true;
}

bool ConsentManager::set_consent(bool opted_in) {
    std::lock_guard<std::mutex> lock(consent_mutex_);

    if (!save_consent(opted_in)) {
        return false;
    }

    opted_in_ = opted_in;

    return true;
}

}  // namespace acr
