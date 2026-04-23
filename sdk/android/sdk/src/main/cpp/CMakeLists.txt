cmake_minimum_required(VERSION 3.22.1)
project(synora_sdk_android CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN ON)

# Pull the fingerprint algorithm from the shared SDK source tree so Android
# and desktop/Linux use the exact same implementation.
set(SDK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../../..")

add_library(synora_sdk SHARED
    jni_bridge.cpp
    "${SDK_ROOT}/src/fingerprint.cpp"
)

target_include_directories(synora_sdk PRIVATE
    "${SDK_ROOT}/include"
    "${SDK_ROOT}/src"
)

# On Android we skip OpenSSL: the fingerprint algorithm itself does not need
# SHA-256, and we do SHA-256 in Kotlin (java.security.MessageDigest) where
# device-specific salting already lives.

find_library(log-lib log)
target_link_libraries(synora_sdk PRIVATE ${log-lib})

target_compile_options(synora_sdk PRIVATE -Wall -Wextra -Wno-unused-parameter)
