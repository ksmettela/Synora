# ACRaaS SDK - Build Guide

Complete instructions for building the ACRaaS SDK on various platforms.

## Prerequisites

### System Requirements

- CMake 3.20 or later
- C++ compiler with C++17 support (GCC 7+, Clang 5+)
- Linux kernel with ALSA support

### Dependency Installation

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    git \
    libssl-dev \
    libasound2-dev \
    libcurl4-openssl-dev \
    libsqlite3-dev \
    libc-dev
```

#### CentOS/RHEL/Fedora

```bash
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    cmake \
    pkg-config \
    git \
    openssl-devel \
    alsa-lib-devel \
    libcurl-devel \
    sqlite-devel
```

#### Alpine

```bash
apk add --no-cache \
    build-base \
    cmake \
    pkgconfig \
    openssl-dev \
    alsa-lib-dev \
    curl-dev \
    sqlite-dev
```

#### macOS (for cross-compilation)

```bash
brew install cmake openssl curl sqlite3 pkg-config
```

## Building

### Standard Linux Build

```bash
cd acraas/sdk
mkdir build && cd build
cmake ..
make -j$(nproc)
```

**Output:**
- `libacr.so` - Shared library
- `libacr.a` - Static library (if configured)

### Build Options

#### With Tests

```bash
cmake -DBUILD_TESTS=ON ..
make -j$(nproc)
ctest --verbose
```

#### With Debug Symbols

```bash
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)
```

#### With Optimizations

```bash
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

#### Verbose Build

```bash
cmake -DCMAKE_VERBOSE_MAKEFILE=ON ..
make
```

### Installation

```bash
cd build
sudo make install
```

Default install paths:
- Libraries: `/usr/local/lib/`
- Headers: `/usr/local/include/`

Custom install path:

```bash
cmake -DCMAKE_INSTALL_PREFIX=/opt/acr ..
make install
```

## Platform-Specific Builds

### Tizen (Samsung TV OS)

#### 1. Install Tizen SDK

```bash
# Download from: https://developer.tizen.org/development/tizen-studio/download

# Source Tizen environment
source ~/tizen-studio/tools/ide/bin/tizen-studio-env.sh
```

#### 2. Create Tizen Toolchain (optional)

Create `toolchain/tizen.cmake`:

```cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR arm)

set(CMAKE_C_COMPILER arm-linux-gnueabihf-gcc)
set(CMAKE_CXX_COMPILER arm-linux-gnueabihf-g++)

set(CMAKE_FIND_ROOT_PATH /opt/tizen-sdk/sysroots/armv7l-tizen-linux-gnueabi)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

add_compile_options(-march=armv7-a -mtune=cortex-a9)
```

#### 3. Build for Tizen

```bash
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../toolchain/tizen.cmake ..
make -j$(nproc)
```

### webOS (LG TV OS)

#### 1. Install webOS SDK

```bash
# Download from: https://webostv.developer.lge.com/sdk/download/

source /opt/webos-sdk-x86_64/environment-setup-core2-32-webos-linux
```

#### 2. Build for webOS

```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

The SDK environment provides all necessary cross-compilation settings.

### Android TV

#### Prerequisites

```bash
# Download Android NDK
# From: https://developer.android.com/ndk/downloads/

export NDK_PATH=/path/to/android-ndk-r21
```

#### Build for ARM (32-bit)

```bash
mkdir build && cd build
cmake -DBUILD_ANDROID=ON \
    -DCMAKE_TOOLCHAIN_FILE=$NDK_PATH/build/cmake/android.toolchain.cmake \
    -DANDROID_PLATFORM=android-21 \
    -DANDROID_ABI=armeabi-v7a \
    -DCMAKE_BUILD_TYPE=Release \
    ..
make -j$(nproc)
```

#### Build for ARM64 (64-bit)

```bash
mkdir build && cd build
cmake -DBUILD_ANDROID=ON \
    -DCMAKE_TOOLCHAIN_FILE=$NDK_PATH/build/cmake/android.toolchain.cmake \
    -DANDROID_PLATFORM=android-21 \
    -DANDROID_ABI=arm64-v8a \
    -DCMAKE_BUILD_TYPE=Release \
    ..
make -j$(nproc)
```

#### Build for x86

```bash
cmake -DANDROID_ABI=x86 \
    -DANDROID_PLATFORM=android-21 \
    ...
```

#### Build for x86_64

```bash
cmake -DANDROID_ABI=x86_64 \
    -DANDROID_PLATFORM=android-21 \
    ...
```

#### Android Build Output

```
build/src/libacr.so
build/android/libacr_jni.so
```

### Cross-Compilation (Generic)

For other ARM platforms, create a custom toolchain:

```bash
# Create toolchain-arm.cmake
cmake_minimum_required(VERSION 3.20)

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR arm)

set(CROSS_COMPILE /path/to/toolchain/arm-linux-gnueabihf-)
set(CMAKE_C_COMPILER ${CROSS_COMPILE}gcc)
set(CMAKE_CXX_COMPILER ${CROSS_COMPILE}g++)
set(CMAKE_AR ${CROSS_COMPILE}ar)
set(CMAKE_RANLIB ${CROSS_COMPILE}ranlib)

set(CMAKE_FIND_ROOT_PATH /path/to/sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
```

Build with:

```bash
cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-arm.cmake ..
```

## Troubleshooting

### CMake Not Found

```bash
# Ensure CMake >= 3.20
cmake --version

# If too old, install newer version:
sudo apt-get install cmake   # or download from cmake.org
```

### OpenSSL Not Found

```bash
# Install development package
sudo apt-get install libssl-dev

# Or specify manually:
cmake -DOPENSSL_DIR=/usr/local/ssl ..
```

### ALSA Not Found

```bash
# Install ALSA development package
sudo apt-get install libasound2-dev

# Or check ALSA installation:
pkg-config --cflags --libs alsa
```

### libcurl Not Found

```bash
# Install curl development package
sudo apt-get install libcurl4-openssl-dev

# Verify installation:
pkg-config --cflags --libs libcurl
```

### SQLite3 Not Found

```bash
# Install SQLite3 development package
sudo apt-get install libsqlite3-dev

# Verify:
sqlite3 --version
```

### Compilation Errors

#### "No matching function for call to 'snd_pcm_readi'"

ALSA headers not found. Install: `sudo apt-get install libasound2-dev`

#### "undefined reference to 'curl_easy_init'"

libcurl not linked. Verify libcurl is installed and pkg-config can find it.

#### "'std::make_unique' is not a member of 'std'"

C++17 not enabled. Check CMakeLists.txt has `set(CMAKE_CXX_STANDARD 17)`

#### "Cannot open shared object file: libcurl.so.4"

Library not in library path. Add to `LD_LIBRARY_PATH`:

```bash
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
```

Or use rpath during build:

```bash
cmake -DCMAKE_BUILD_RPATH=/usr/local/lib ..
```

## Build Configuration

### CMakeLists.txt Variables

Key variables you can override:

```bash
# Install prefix
-DCMAKE_INSTALL_PREFIX=/custom/path

# Build type (Debug, Release, RelWithDebInfo, MinSizeRel)
-DCMAKE_BUILD_TYPE=Release

# Enable tests
-DBUILD_TESTS=ON

# Enable Android build
-DBUILD_ANDROID=ON

# Verbose output
-DCMAKE_VERBOSE_MAKEFILE=ON

# Number of parallel jobs
make -j8
```

## Verifying Installation

After `make install`:

```bash
# Check header
ls -l /usr/local/include/acr.h

# Check libraries
ls -l /usr/local/lib/libacr.*

# Test with pkg-config
pkg-config --cflags --libs libacr

# Compile a simple test
gcc -c test.c `pkg-config --cflags acr`
gcc -o test test.o `pkg-config --libs acr`
./test
```

## Running Tests

```bash
cd build
ctest --verbose

# Run specific test
ctest -R test_name -V

# Run with output
ctest -N                    # List tests
ctest -R fingerprint -V     # Run tests matching pattern
```

## Performance Build

For production deployments:

```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_FLAGS="-O3 -march=native -flto" \
      -DCMAKE_EXE_LINKER_FLAGS="-flto" \
      ..
make -j$(nproc)
```

## Static vs Shared Library

Build both:

```bash
# By default, both libacr.so and libacr.a are built

# Use shared library
gcc -o app app.c -lacr

# Use static library
gcc -o app app.c -static -lacr
```

## Generating Documentation

Install Doxygen:

```bash
sudo apt-get install doxygen graphviz
```

Generate docs:

```bash
doxygen Doxyfile
# Output in docs/html/index.html
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            cmake \
            libssl-dev \
            libasound2-dev \
            libcurl4-openssl-dev \
            libsqlite3-dev
      
      - name: Build
        run: |
          cd acraas/sdk
          mkdir build && cd build
          cmake ..
          make -j$(nproc)
      
      - name: Test
        run: |
          cd acraas/sdk/build
          ctest --verbose
```

## Building Distribution Packages

### DEB Package (Debian/Ubuntu)

Create `debian/control`:

```
Package: acraas-sdk
Version: 1.0.0
Architecture: armhf
Depends: libssl1.1, libasound2, libcurl4, libsqlite3-0
...
```

Build package:

```bash
dpkg-buildpackage -us -uc
```

### RPM Package (CentOS/RHEL)

Create `.spec` file and build:

```bash
rpmbuild -ba acraas-sdk.spec
```

## Clean Build

```bash
# Remove build directory
rm -rf build

# Clean specific component
make -C build clean

# Full distclean
make -C build distclean
```
