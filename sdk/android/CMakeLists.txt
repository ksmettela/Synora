cmake_minimum_required(VERSION 3.20)

# Android NDK build configuration for Synora SDK

# Find required packages for Android
find_package(OpenSSL REQUIRED)
find_package(ALSA REQUIRED)
find_package(CURL REQUIRED)
find_package(SQLite3 REQUIRED)
find_package(Threads REQUIRED)

# Set up Java/JNI
find_package(Java REQUIRED)
find_package(JNI REQUIRED)

# Android native library
add_library(acr_jni SHARED
    AcrJniWrapper.cpp
    ../src/fingerprint.cpp
    ../src/device_id.cpp
    ../src/cache.cpp
    ../src/network.cpp
    ../src/audio_capture.cpp
    ../src/consent.cpp
    ../src/acr.cpp
)

# Include directories
target_include_directories(acr_jni
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/..
        ${CMAKE_CURRENT_SOURCE_DIR}/../include
        ${CMAKE_CURRENT_SOURCE_DIR}/../src
        ${JNI_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(acr_jni
    PRIVATE
        OpenSSL::Crypto
        ALSA::ALSA
        CURL::libcurl
        SQLite3::SQLite3
        Threads::Threads
)

# Compiler options
target_compile_options(acr_jni PRIVATE
    -Wall
    -Wextra
    -Wpedantic
    -Werror=format
    -fvisibility=hidden
    -fPIC
)

# Set library name
set_target_properties(acr_jni PROPERTIES
    OUTPUT_NAME acr
)

# Installation
install(TARGETS acr_jni
    LIBRARY DESTINATION lib
)
