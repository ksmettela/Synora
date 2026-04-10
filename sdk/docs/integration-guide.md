# ACRaaS SDK Integration Guide

## Overview

The ACRaaS (Automatic Content Recognition as a Service) SDK is a C++17 embedded library for TV manufacturers to integrate into their firmware. It performs automatic content recognition by capturing audio, generating fingerprints, and transmitting them to the ACRaaS ingest server.

## Requirements

### System Requirements

- **Linux-based TV OS** (Tizen, webOS, Android TV, custom)
- **Architecture**: ARM (32/64-bit), x86, or x86_64
- **Kernel**: Linux 3.10+ with ALSA support
- **Libc**: glibc 2.17+ or musl 1.1.15+

### Dependencies

#### Build Time
- CMake 3.20+
- GCC 7+ or Clang 5+ (C++17 support)
- pkg-config

#### Runtime Libraries
- OpenSSL 1.1.0+ (libssl, libcrypto)
- ALSA 1.0.27+ (libasound)
- libcurl 7.60+
- SQLite3 3.8.0+
- POSIX Threads (libpthread)

### Linux Distribution Support

#### Tizen (Samsung TV OS)
- Tizen 5.5+
- Use Tizen SDK with cross-compiler

#### webOS (LG TV OS)
- webOS 3.0+
- Use webOS SDK with cross-compiler

#### Android TV
- Android 5.0 (API 21)+
- Use Android NDK (r21+)

## Installation

### Prerequisites Setup

#### For Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y \
    cmake \
    build-essential \
    pkg-config \
    libssl-dev \
    libasound2-dev \
    libcurl4-openssl-dev \
    libsqlite3-dev
```

#### For CentOS/RHEL
```bash
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    cmake \
    openssl-devel \
    alsa-lib-devel \
    libcurl-devel \
    sqlite-devel
```

### Building the SDK

#### Standard Linux Build

```bash
cd acraas/sdk
mkdir build && cd build
cmake ..
make -j$(nproc)
```

This creates:
- `libacr.so` - Shared library (dynamically linked)
- `libacr.a` - Static library (statically linked)

#### With Tests

```bash
mkdir build && cd build
cmake -DBUILD_TESTS=ON ..
make -j$(nproc)
ctest
```

#### Android Build

```bash
mkdir build && cd build
cmake -DBUILD_ANDROID=ON \
    -DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake \
    -DANDROID_PLATFORM=android-21 \
    -DANDROID_ABI=armeabi-v7a \
    ..
make -j$(nproc)
```

Supported ABI values:
- `armeabi-v7a` - 32-bit ARM (most TV boxes)
- `arm64-v8a` - 64-bit ARM
- `x86` - 32-bit Intel
- `x86_64` - 64-bit Intel

#### Tizen Build

```bash
source $TIZEN_SDK_DIR/environment-setup-*-tizen-linux-gnueabi
cd acraas/sdk
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../toolchain/tizen.cmake ..
make -j$(nproc)
```

#### webOS Build

```bash
source /opt/webos-sdk-x86_64/environment-setup-*-webos-linux-gnueabi
cd acraas/sdk
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../toolchain/webos.cmake ..
make -j$(nproc)
```

### Installation

```bash
cd build
sudo make install
```

This installs to:
- `/usr/local/lib/libacr.so`
- `/usr/local/lib/libacr.a`
- `/usr/local/include/acr.h`

## Integration Steps

### 1. Include Header

```c
#include <acr.h>
```

### 2. Initialize SDK

```c
acr_config_t config = {
    .server_url = "https://acr-ingest.example.com",
    .api_key = "your-api-key",
    .batch_size = 20,
    .flush_interval_sec = 60,
    .sample_rate_hz = 16000,
    .capture_duration_ms = 3000,
    .capture_interval_sec = 30,
};

acr_error_t err = acr_init(&config);
if (err != ACR_SUCCESS) {
    perror("Failed to init ACR SDK");
    return;
}
```

### 3. Start Capture

```c
err = acr_start();
if (err != ACR_SUCCESS) {
    perror("Failed to start capture");
    return;
}
```

### 4. Handle User Consent

```c
// User enables ACR in settings
acr_set_consent(true);

// User disables ACR in settings
// This stops capture and purges all cached data
acr_set_consent(false);
```

### 5. Stop Capture

```c
// When shutting down TV or disabling ACR
acr_stop();
```

### Minimal Example

```c
#include <acr.h>
#include <stdio.h>
#include <unistd.h>

int main() {
    acr_config_t config = {
        .server_url = "https://acr.example.com",
        .api_key = "demo-key",
    };

    if (acr_init(&config) != ACR_SUCCESS) {
        fprintf(stderr, "Init failed\n");
        return 1;
    }

    acr_set_consent(true);
    acr_start();

    // Run for 60 seconds
    sleep(60);

    // Flush remaining data
    acr_flush();
    acr_stop();

    return 0;
}
```

## Android Integration

### Kotlin Example

```kotlin
import io.acraas.sdk.AcrSdk

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize
        val config = AcrSdk.Config(
            serverUrl = "https://acr.example.com",
            apiKey = "your-api-key"
        )

        val result = AcrSdk.init(config)
        if (result != AcrSdk.ErrorCode.SUCCESS) {
            Log.e("ACR", "Init failed: $result")
            return
        }

        // Start
        AcrSdk.setConsent(true)
        AcrSdk.start()
    }

    override fun onDestroy() {
        super.onDestroy()
        AcrSdk.flush()
        AcrSdk.stop()
    }

    fun handleUserConsent(optedIn: Boolean) {
        AcrSdk.setConsent(optedIn)
    }
}
```

### Java Example

```java
import io.acraas.sdk.AcrSdk;

public class MainActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        AcrSdk.Config config = new AcrSdk.Config(
            "https://acr.example.com",
            "your-api-key",
            20,      // batchSize
            60,      // flushIntervalSec
            16000,   // sampleRateHz
            3000,    // captureDurationMs
            30       // captureIntervalSec
        );

        int result = AcrSdk.init(config);
        if (result != AcrSdk.ErrorCode.SUCCESS) {
            Log.e("ACR", "Init failed");
            return;
        }

        AcrSdk.setConsent(true);
        AcrSdk.start();
    }
}
```

## Privacy Best Practices

### User Consent

1. **Display Privacy Disclosure**: Show users a clear explanation of what ACR does
2. **Opt-In Default**: ACR should be off by default
3. **Easy Disable**: Provide prominent settings to disable ACR
4. **Respect Consent**: Honor user choice immediately

### Data Protection

1. **Local Caching**: Fingerprints cached in `/var/lib/acr/` with restricted permissions (0600)
2. **Encryption**: Use TLS 1.2+ for all network transmission
3. **No Audio Storage**: Raw audio is never stored, only fingerprints
4. **Automatic Purge**: Old data purged after 7 days
5. **Cache Clearing**: When user opts-out, all cache is purged immediately

### Compliance

- **GDPR**: Implement user consent and data deletion
- **CCPA**: Honor user privacy preferences
- **Regional Laws**: Check local TV/privacy regulations

## Network Configuration

### Server URL Format

```
https://acr-ingest.example.com/v1/fingerprints/ingest
```

### Batch Transmission

- Default: 20 fingerprints per batch
- Configurable via `batch_size` in config
- Transmitted when batch full OR `flush_interval_sec` elapsed

### Error Handling

```c
acr_error_t err = acr_init(&config);

switch (err) {
    case ACR_SUCCESS:
        // OK
        break;
    case ACR_ERROR_INIT:
        // Initialization failed (bad config, missing dependencies)
        break;
    case ACR_ERROR_NETWORK:
        // Network error (no connectivity, server error)
        break;
    case ACR_ERROR_CONSENT:
        // User consent not granted
        break;
    case ACR_ERROR_AUDIO:
        // Audio capture failed (no ALSA, hardware issue)
        break;
}
```

## Troubleshooting

### Audio Capture Not Working

1. Check ALSA installation: `aplay -l`
2. Verify audio device: `cat /proc/asound/devices`
3. Check permissions: Ensure process can access `/dev/snd/*`
4. Logs will show: "Cannot open audio device"

### Network Transmission Failing

1. Check connectivity: `ping acr-ingest.example.com`
2. Verify API key: Compare with server configuration
3. Check certificate: `curl -v https://acr-ingest.example.com`
4. Review firewall: Ensure port 443 (HTTPS) is open

### High CPU Usage

Target: < 2% CPU usage

If exceeded:
1. Increase `capture_interval_sec` (longer gaps between captures)
2. Reduce `capture_duration_ms` (shorter audio samples)
3. Lower `sample_rate_hz` (lower quality, less processing)

### Permission Denied Errors

1. Create `/var/lib/acr` directory: `sudo mkdir -p /var/lib/acr`
2. Set permissions: `sudo chmod 755 /var/lib/acr`
3. Ensure writable by TV process user

### SQLite "Database Locked" Errors

1. Check disk space: `df /var/lib/acr`
2. Verify permissions: `ls -la /var/lib/acr/`
3. Clear old data: Manual purge if storage full

## Performance Tuning

### Low-Power Devices (TV Boxes)

```c
acr_config_t config = {
    .capture_interval_sec = 60,     // Capture every 60s instead of 30s
    .capture_duration_ms = 2000,    // Shorter samples
    .batch_size = 10,               // Smaller batches
    .flush_interval_sec = 120,      // Less frequent flushes
    .sample_rate_hz = 16000,
};
```

### High-Performance Devices

```c
acr_config_t config = {
    .capture_interval_sec = 15,     // Frequent sampling
    .capture_duration_ms = 5000,    // Longer samples for accuracy
    .batch_size = 50,               // Larger batches
    .flush_interval_sec = 30,       // Frequent transmission
    .sample_rate_hz = 16000,
};
```

## API Reference

### acr_init()

```c
acr_error_t acr_init(const acr_config_t* config);
```

Initializes the SDK. Must be called once before any other function.

### acr_start()

```c
acr_error_t acr_start(void);
```

Starts audio capture and transmission. Respects user consent.

### acr_stop()

```c
acr_error_t acr_stop(void);
```

Stops capture and transmission. Flushes remaining data.

### acr_set_consent()

```c
acr_error_t acr_set_consent(bool opted_in);
```

Sets user consent. When false, clears all cached data.

### acr_flush()

```c
acr_error_t acr_flush(void);
```

Forces immediate transmission of cached fingerprints.

### acr_get_device_id()

```c
acr_error_t acr_get_device_id(char* buf, size_t len);
```

Gets stable device ID. Buffer should be at least 64 bytes.

### acr_version()

```c
const char* acr_version(void);
```

Returns SDK version string (e.g., "1.0.0").

## Support & Documentation

- **GitHub**: https://github.com/acraas/sdk
- **Issue Tracker**: https://github.com/acraas/sdk/issues
- **API Documentation**: https://docs.acraas.io
- **Email**: support@acraas.io
