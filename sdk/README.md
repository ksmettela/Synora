# Synora SDK - Automatic Content Recognition as a Service

A production-grade C++17 embedded library for TV manufacturers to integrate Automatic Content Recognition into their firmware.

## Features

- **Audio Fingerprinting**: Spectral peak-based fingerprinting with Cooley-Tukey FFT
- **Local Caching**: SQLite database with automatic purging and transmission queue
- **Batch Transmission**: Efficient HTTP POST with JSON payloads and exponential backoff
- **ALSA Audio Capture**: Low-latency audio sampling with error recovery
- **Device Identification**: Stable SHA256-based device IDs from MAC + hardware info
- **User Consent**: Persistent consent management with automatic cache purging
- **Android Support**: Full JNI bindings for Kotlin/Java integration
- **Thread-Safe**: All components protected with mutexes
- **Low CPU Impact**: Target < 2% CPU usage with configurable sampling

## Project Structure

```
acraas/sdk/
├── include/
│   └── acr.h                 # Public C ABI header
├── src/
│   ├── fingerprint.hpp/.cpp  # Audio fingerprinting engine
│   ├── device_id.hpp/.cpp    # Stable device ID generation
│   ├── cache.hpp/.cpp        # SQLite fingerprint cache
│   ├── network.hpp/.cpp      # HTTP batch transmission client
│   ├── audio_capture.hpp/.cpp # ALSA audio capture
│   ├── consent.hpp/.cpp      # Consent management
│   ├── acr.cpp               # Main SDK implementation
│   └── test_main.cpp         # Test program
├── android/
│   ├── AcrSdk.kt             # Kotlin JNI wrapper
│   ├── AcrJniWrapper.cpp     # JNI implementation
│   └── CMakeLists.txt        # Android build config
├── docs/
│   └── integration-guide.md  # Detailed integration guide
├── CMakeLists.txt            # Main build configuration
└── README.md                 # This file
```

## Quick Start

### Build

```bash
cd acraas/sdk
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Test

```bash
cmake -DBUILD_TESTS=ON ..
make
ctest
```

### Integration Example (C)

```c
#include <acr.h>

int main() {
    acr_config_t config = {
        .server_url = "https://acr-ingest.example.com",
        .api_key = "your-api-key",
    };

    acr_init(&config);
    acr_set_consent(true);
    acr_start();

    // ... run for a while ...

    acr_flush();
    acr_stop();

    return 0;
}
```

### Integration Example (Kotlin/Android)

```kotlin
import io.acraas.sdk.AcrSdk

val config = AcrSdk.Config(
    serverUrl = "https://acr-ingest.example.com",
    apiKey = "your-api-key"
)

AcrSdk.init(config)
AcrSdk.setConsent(true)
AcrSdk.start()

// ... later ...

AcrSdk.stop()
```

## System Requirements

- **OS**: Linux 3.10+ (Tizen, webOS, Android, custom)
- **Architecture**: ARM, x86, or x86_64
- **Libc**: glibc 2.17+ or musl 1.1.15+
- **Dependencies**: OpenSSL, ALSA, libcurl, SQLite3

## Key Components

### Fingerprinting Engine
- Converts 3-second PCM audio to 256-bit fingerprint
- Applies Hann window, Cooley-Tukey FFT, spectral peak extraction
- Uses combinatorial hashing for fingerprint generation

### Device ID Manager
- Generates stable SHA256 hash from MAC + manufacturer + model
- Caches in `/var/lib/acr/device_id`
- Consistent across reboots

### Fingerprint Cache
- SQLite database at `/var/lib/acr/fingerprint_cache.db`
- Stores up to 500 fingerprints with transmission status
- WAL mode for performance
- Thread-safe access

### Network Client
- Background transmission thread
- Exponential backoff: 1s → 2s → 4s → ... → 300s
- TLS 1.2+ verification
- Timeouts: 10s connect, 30s read

### Audio Capture
- ALSA PCM capture from default device
- 16kHz mono, 16-bit signed samples
- Background capture thread
- EPIPE/underrun recovery

### Consent Manager
- Persistent storage in `/var/lib/acr/consent`
- When disabled: stops capture, purges cache
- File-based (opted_in/opted_out)

## API Documentation

See `include/acr.h` for complete C API.

### Main Functions

- `acr_init(config)` - Initialize SDK
- `acr_start()` - Start capture
- `acr_stop()` - Stop capture
- `acr_set_consent(bool)` - Set user consent
- `acr_flush()` - Force transmission
- `acr_get_device_id(buf, len)` - Get device ID
- `acr_version()` - Get version

## Integration Guide

See `docs/integration-guide.md` for:
- Detailed platform-specific build instructions
- Privacy best practices
- Network configuration
- Error handling
- Performance tuning
- Troubleshooting

## Privacy

The SDK respects user privacy:

1. **Opt-In Default**: ACR is disabled until explicitly enabled
2. **No Audio Storage**: Only fingerprints are stored, never raw audio
3. **Automatic Purging**: Data deleted after 7 days or on user opt-out
4. **Secure Storage**: File permissions 0600, encrypted transmission with TLS
5. **Compliance Ready**: GDPR, CCPA, and regional TV regulations

## Performance

- **CPU**: < 2% target (configurable sampling intervals)
- **Memory**: ~10-20 MB resident
- **Network**: Batch transmission with exponential backoff
- **Disk**: Up to 50 MB for 500 cached fingerprints

## Build Options

```bash
cmake -DBUILD_TESTS=ON ..          # Include test programs
cmake -DBUILD_ANDROID=ON ..        # Build Android NDK library
```

## Installation

```bash
cd build
sudo make install
```

Installs to:
- `/usr/local/lib/libacr.so`
- `/usr/local/lib/libacr.a`
- `/usr/local/include/acr.h`

## Supported Platforms

- **Linux**: Any glibc/musl-based distribution
- **Tizen**: Samsung Smart TVs (5.5+)
- **webOS**: LG Smart TVs (3.0+)
- **Android TV**: Google Android TV (5.0+)
- **Custom**: Any Linux TV OS with ALSA + libcurl

## License

[Your License Here]

## Support

- Documentation: See `docs/integration-guide.md`
- Issues: [Your GitHub Issues URL]
- Email: [Your Support Email]

## Version

Current version: **1.0.0**

See `acr_version()` to query at runtime.
