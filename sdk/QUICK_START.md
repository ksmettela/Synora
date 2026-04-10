# ACRaaS SDK - Quick Start Guide

Get the ACRaaS SDK built and integrated in 5 minutes.

## Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config \
    libssl-dev libasound2-dev libcurl4-openssl-dev libsqlite3-dev

# CentOS/RHEL
sudo yum groupinstall -y "Development Tools"
sudo yum install -y cmake pkg-config openssl-devel alsa-lib-devel \
    libcurl-devel sqlite-devel
```

## Build

```bash
cd acraas/sdk
mkdir build && cd build
cmake ..
make -j$(nproc)
```

Output:
- `libacr.so` - Shared library
- `libacr.a` - Static library

## Install

```bash
sudo make install
```

## Simple C Example

```c
#include <acr.h>
#include <stdio.h>
#include <unistd.h>

int main() {
    // Configure
    acr_config_t config = {
        .server_url = "https://acr.example.com",
        .api_key = "your-api-key",
    };

    // Initialize
    if (acr_init(&config) != ACR_SUCCESS) {
        perror("acr_init");
        return 1;
    }

    // Get device ID
    char device_id[256];
    acr_get_device_id(device_id, sizeof(device_id));
    printf("Device ID: %s\n", device_id);

    // Enable and start
    acr_set_consent(true);
    acr_start();

    // Run for 60 seconds
    sleep(60);

    // Cleanup
    acr_flush();
    acr_stop();

    return 0;
}
```

Compile:
```bash
gcc -o app app.c -lacr
./app
```

## Simple Kotlin/Android Example

```kotlin
import io.acraas.sdk.AcrSdk

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Configure
        val config = AcrSdk.Config(
            serverUrl = "https://acr.example.com",
            apiKey = "your-api-key"
        )

        // Initialize
        val result = AcrSdk.init(config)
        if (result != AcrSdk.ErrorCode.SUCCESS) {
            Log.e("ACR", "Init failed: $result")
            return
        }

        // Start capture
        AcrSdk.setConsent(true)
        AcrSdk.start()
    }

    override fun onDestroy() {
        super.onDestroy()
        AcrSdk.flush()
        AcrSdk.stop()
    }
}
```

## API Quick Reference

```c
// Initialize (must call first)
acr_init(&config);

// Start capture
acr_start();

// Stop capture
acr_stop();

// Set user consent
acr_set_consent(true);  // Enable
acr_set_consent(false); // Disable and purge

// Force transmission
acr_flush();

// Get device ID
acr_get_device_id(buf, len);

// Get version
acr_version();
```

## Error Codes

```c
ACR_SUCCESS          // 0   - OK
ACR_ERROR_INIT       // -1  - Initialization failed
ACR_ERROR_NETWORK    // -2  - Network error
ACR_ERROR_CONSENT    // -3  - User consent not granted
ACR_ERROR_AUDIO      // -4  - Audio capture error
```

## Configuration Defaults

```c
acr_config_t config = {
    .server_url = "https://...",         // Required
    .api_key = "...",                    // Required
    .batch_size = 20,                    // fingerprints/batch
    .flush_interval_sec = 60,            // seconds
    .sample_rate_hz = 16000,             // Hz
    .capture_duration_ms = 3000,         // milliseconds
    .capture_interval_sec = 30,          // seconds
};
```

## Testing

```bash
# Build with tests
cmake -DBUILD_TESTS=ON ..
make

# Run tests
ctest --verbose

# Run test program
./src/test_main
```

## Android Build

```bash
# Set NDK path
export NDK=/path/to/android-ndk-r21

# Build for ARM
mkdir build && cd build
cmake -DBUILD_ANDROID=ON \
    -DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake \
    -DANDROID_PLATFORM=android-21 \
    -DANDROID_ABI=armeabi-v7a \
    ..
make -j$(nproc)
```

## Common Issues

**Problem: "Cannot find OpenSSL"**
```bash
sudo apt-get install libssl-dev
```

**Problem: "Cannot find ALSA"**
```bash
sudo apt-get install libasound2-dev
aplay -l  # Verify ALSA works
```

**Problem: "Cannot find libcurl"**
```bash
sudo apt-get install libcurl4-openssl-dev
```

**Problem: "C++17 not supported"**
```bash
gcc --version  # Need GCC 7+
# Update compiler if needed
```

## Storage Paths

- Device ID: `/var/lib/acr/device_id`
- Cache DB: `/var/lib/acr/fingerprint_cache.db`
- Consent: `/var/lib/acr/consent`

Create directory:
```bash
sudo mkdir -p /var/lib/acr
sudo chmod 755 /var/lib/acr
```

## Performance Tuning

**Low-power device** (< 2% CPU):
```c
config.capture_interval_sec = 60;   // Every 60 seconds
config.capture_duration_ms = 2000;  // Shorter samples
config.batch_size = 10;             // Smaller batches
```

**High-performance device**:
```c
config.capture_interval_sec = 15;   // Every 15 seconds
config.capture_duration_ms = 5000;  // Longer samples
config.batch_size = 50;             // Larger batches
```

## Documentation

- **API Reference**: `docs/api-reference.md`
- **Integration Guide**: `docs/integration-guide.md`
- **Build Guide**: `docs/build-guide.md`
- **Project Overview**: `README.md`

## Architecture Overview

```
┌─────────────────────────────────────┐
│         Application Layer           │
├─────────────────────────────────────┤
│   Public C API (acr.h)              │
├─────────────────────────────────────┤
│  ┌──────────┬──────────┬──────────┐ │
│  │ Audio    │Fingerp.  │ Device   │ │
│  │ Capture  │ Engine   │ ID       │ │
│  └──────────┴──────────┴──────────┘ │
│  ┌──────────┬──────────┬──────────┐ │
│  │ Cache    │ Network  │ Consent  │ │
│  │ (SQLite) │ (curl)   │ (file)   │ │
│  └──────────┴──────────┴──────────┘ │
├─────────────────────────────────────┤
│  System Libraries                   │
│  (ALSA, OpenSSL, libcurl, SQLite)   │
├─────────────────────────────────────┤
│         Linux Kernel                │
└─────────────────────────────────────┘
```

## Next Steps

1. Build: `make -j$(nproc)`
2. Test: `ctest --verbose`
3. Review: `docs/api-reference.md`
4. Integrate: `docs/integration-guide.md`
5. Deploy: Link against `libacr.so` or `libacr.a`

## Support

For detailed information, see:
- API: `docs/api-reference.md`
- Build: `docs/build-guide.md`
- Integration: `docs/integration-guide.md`
- Code: `include/acr.h`
