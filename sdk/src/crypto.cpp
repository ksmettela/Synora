#include <openssl/sha.h>

#include <array>
#include <cstdint>
#include <cstring>
#include <sstream>
#include <iomanip>
#include <string>

namespace acr {

std::string sha256_hex(const void* data, size_t len) {
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256(reinterpret_cast<const unsigned char*>(data), len, hash);
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i) {
        oss << std::setw(2) << static_cast<int>(hash[i]);
    }
    return oss.str();
}

std::string sha256_hex(const std::string& data) {
    return sha256_hex(data.data(), data.size());
}

std::string bytes_to_hex(const uint8_t* data, size_t len) {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (size_t i = 0; i < len; ++i) {
        oss << std::setw(2) << static_cast<int>(data[i]);
    }
    return oss.str();
}

std::string bytes_to_hex(const std::array<uint8_t, 32>& data) {
    return bytes_to_hex(data.data(), data.size());
}

}  // namespace acr
