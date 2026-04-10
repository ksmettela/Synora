cmake_minimum_required(VERSION 3.20)
project(acraas-sdk VERSION 1.0.0 LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Options
option(BUILD_TESTS "Build test programs" OFF)
option(BUILD_ANDROID "Build Android NDK library" OFF)

# Find required packages
find_package(OpenSSL REQUIRED)
find_package(ALSA REQUIRED)
find_package(CURL REQUIRED)
find_package(SQLite3 REQUIRED)
find_package(Threads REQUIRED)

# Core library sources
set(ACR_SOURCES
    src/fingerprint.cpp
    src/device_id.cpp
    src/cache.cpp
    src/network.cpp
    src/audio_capture.cpp
    src/consent.cpp
    src/acr.cpp
)

set(ACR_HEADERS
    include/acr.h
    src/fingerprint.hpp
    src/device_id.hpp
    src/cache.hpp
    src/network.hpp
    src/audio_capture.hpp
    src/consent.hpp
)

# Build shared library
add_library(acr SHARED ${ACR_SOURCES})
target_include_directories(acr
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(acr
    PRIVATE
        OpenSSL::Crypto
        ALSA::ALSA
        CURL::libcurl
        SQLite3::SQLite3
        Threads::Threads
)

# Set appropriate compile flags
target_compile_options(acr PRIVATE
    -Wall
    -Wextra
    -Wpedantic
    -Werror=format
    -fvisibility=hidden
)

# Build static library
add_library(acr_static STATIC ${ACR_SOURCES})
target_include_directories(acr_static
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(acr_static
    PUBLIC
        OpenSSL::Crypto
        ALSA::ALSA
        CURL::libcurl
        SQLite3::SQLite3
        Threads::Threads
)

set_target_properties(acr_static PROPERTIES OUTPUT_NAME acr)

# Version information
set_target_properties(acr PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
)

# Installation
install(TARGETS acr acr_static
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(FILES include/acr.h
    DESTINATION include
)

# Optional: Build tests
if(BUILD_TESTS)
    enable_testing()

    add_executable(acr_test src/test_main.cpp)
    target_link_libraries(acr_test PRIVATE acr)
    add_test(NAME acr_test COMMAND acr_test)
endif()

# Optional: Android NDK support
if(BUILD_ANDROID)
    add_subdirectory(android)
endif()

# Print build info
message(STATUS "Synora SDK ${PROJECT_VERSION}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Shared library: libacr.so")
message(STATUS "Static library: libacr.a")
