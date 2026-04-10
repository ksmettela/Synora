#pragma once

#include <string>
#include <map>
#include <memory>

namespace acraas {

class FingerprintRequest {
public:
    std::string device_id;
    std::string user_agent;
    std::string ip_address;
    std::map<std::string, std::string> metadata;
    long timestamp;
};

class Client {
public:
    Client(const std::string& endpoint, const std::string& api_key);
    ~Client();
    
    bool submit_fingerprint(const FingerprintRequest& request);
    std::string generate_fingerprint();
    
private:
    std::string endpoint_;
    std::string api_key_;
};

} // namespace acraas
