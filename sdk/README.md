# Synora SDK

C++17 embedded library for TV manufacturers to integrate Automatic Content
Recognition into their firmware. Same fingerprint algorithm runs on the
device, in the seeding pipeline, and in the end-to-end test suite.

## Layout

```
sdk/
├── include/acr.h              # Public C ABI
├── src/
│   ├── fingerprint.cpp/.hpp   # FFT + averaged log-spectrum fingerprint
│   ├── crypto.cpp/.hpp        # SHA-256 (OpenSSL)
│   ├── device_id.cpp/.hpp     # Stable device ID generation
│   ├── cache.cpp/.hpp         # SQLite fingerprint cache
│   ├── network.cpp/.hpp       # HTTP batch transmission
│   ├── audio_capture.cpp/.hpp # ALSA audio capture (Linux/Tizen/webOS)
│   ├── consent.cpp/.hpp       # Consent manager
│   └── acr.cpp                # Public API implementation
├── tools/fingerprint_cli.cpp  # WAV → fingerprint CLI (used by seeder/tests)
├── android/                   # Android Gradle module (see android/README.md)
└── CMakeLists.txt
```

## Build

### Full device SDK (Linux)

```bash
cd sdk
mkdir build && cd build
cmake ..
make -j$(nproc)
```

Deps: OpenSSL, ALSA, libcurl, SQLite3, pthread.

### fingerprint_cli only (any platform)

Skip ALSA/libcurl/SQLite if you only need the CLI (e.g. for the seeder on
macOS dev machines or CI):

```bash
cmake -DBUILD_SDK_LIB=OFF ..
make fingerprint_cli
```

Or compile it directly without CMake:

```bash
clang++ -std=c++17 -O2 -Iinclude -Isrc \
  tools/fingerprint_cli.cpp src/fingerprint.cpp src/crypto.cpp \
  -lcrypto -o fingerprint_cli
```

### Android

See [`android/README.md`](android/README.md). The Android module shares
`src/fingerprint.cpp` with the Linux build but skips ALSA/libcurl/SQLite —
Kotlin owns audio capture, cache, and network.

### Tests

```bash
cmake -DBUILD_TESTS=ON ..
make && ctest
```

## CMake options

| Option | Default | Purpose |
|---|---|---|
| `BUILD_SDK_LIB` | `ON` | Build the full `libacr.{so,a}` device library |
| `BUILD_FINGERPRINT_CLI` | `ON` | Build the standalone `fingerprint_cli` tool |
| `BUILD_TESTS` | `OFF` | Build `acr_test` unit tests |
| `BUILD_ANDROID` | `OFF` | Build under the legacy `android/` CMake path — prefer the Gradle project in `android/` instead |

## Integration (C)

```c
#include <acr.h>

acr_config_t config = {
    .server_url = "https://ingest.synora.example",
    .api_key = "your-api-key",
};
acr_init(&config);
acr_set_consent(true);
acr_start();
// ...
acr_stop();
```

## Host-side fingerprinting

For host platforms that manage audio capture themselves (Android, iOS, or any
non-ALSA TV OS), call `acr_fingerprint_pcm()` directly on a PCM buffer — no
ALSA, no background threads, pure function:

```c
uint8_t fp[32];
acr_fingerprint_pcm(pcm_int16, num_samples, 16000, fp, sizeof(fp));
```

## Fingerprint algorithm

256-bit output derived from the averaged log-magnitude spectrum across all
frames in a 3-second window, split into 257 log-spaced bands across
200-4000 Hz. Each output bit is the sign of the energy difference between
adjacent bands.

- Deterministic — same PCM always yields the same hash.
- Shift-invariant — averaging smooths out sub-window time shifts.
- Same-content distance: 50-70 bits at small offsets.
- Unrelated-content distance: 80-130 bits.

See `docs/sdk-integration-guide.md` (repo root) for the detailed integration
guide, privacy model, and OEM onboarding steps.
