# Synora SDK — Android

Android TV port of the Synora ACR SDK. The C++ fingerprint algorithm is
shared verbatim with the desktop/Linux SDK (via the parent source tree);
everything else (audio capture, cache, network, consent) is idiomatic
Kotlin/Android.

## Modules

- `sdk/` — the Android library. Publishes `io.synora.sdk.SynoraSdk`.
- `sample/` — a sample OEM-style integration. Three buttons: consent /
  start / stop.

## Build

Requires: Android Studio Hedgehog or newer, NDK 26+, JDK 17.

```bash
./gradlew :sdk:assembleRelease
./gradlew :sample:assembleDebug
```

There is no `gradlew` wrapper checked in — run
`gradle wrapper --gradle-version=8.7` once after cloning, or open the
project in Android Studio and let it generate one.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Kotlin (io.synora.sdk)                      │
│  ──────────────────────────────              │
│  SynoraSdk            public API             │
│  AudioCapturer        AudioRecord loop       │
│  FingerprintCache     SQLite (500 cap)       │
│  IngestClient         HttpURLConnection POST │
│  ConsentStore         SharedPreferences      │
│  DeviceIdentity       SHA-256 + monthly salt │
└─────────────────┬───────────────────────────┘
                  │ JNI
┌─────────────────▼───────────────────────────┐
│  C++ (libsynora_sdk.so)                      │
│  ──────────────────────────────              │
│  fingerprint.cpp      SHARED with desktop    │
│  jni_bridge.cpp       PCM → 256-bit hash     │
└──────────────────────────────────────────────┘
```

The native library has **no** ALSA / libcurl / SQLite dependency — the shared
fingerprint algorithm is the only native code. This keeps the APK increment
small (~150 kB per ABI) and avoids pulling an extra TLS stack when the
platform already provides one.

## Consent model

- Default state is opted-out.
- Manufacturer app must call `sdk.setConsent(true)` after a user-facing
  opt-in prompt.
- `sdk.setConsent(false)` purges the local cache immediately (CCPA requires
  this).

## Privacy posture

- No raw audio leaves the device.
- Device ID is `sha256(ANDROID_ID + monthly_salt)`; the salt rolls monthly
  so the ID is not linkable across months.
- Full IP is not transmitted; the ingestor truncates to /24 on arrival.
