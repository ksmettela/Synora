#ifndef ACR_CRYPTO_HPP
#define ACR_CRYPTO_HPP

#include <array>
#include <cstdint>
#include <string>

namespace acr {

std::string sha256_hex(const void* data, size_t len);
std::string sha256_hex(const std::string& data);

std::string bytes_to_hex(const uint8_t* data, size_t len);
std::string bytes_to_hex(const std::array<uint8_t, 32>& data);

}  // namespace acr

#endif  // ACR_CRYPTO_HPP
