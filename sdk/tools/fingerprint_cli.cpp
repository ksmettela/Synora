// fingerprint_cli: read a WAV file, emit 256-bit Haitsma-Kalker fingerprints
// as hex strings, one per 3-second window.
//
// Usage:
//   fingerprint_cli <path/to/file.wav> [--window-ms 3000] [--hop-ms 1500]
//
// Output (stdout, one line per window):
//   <start_ms> <fingerprint_hex>
//
// This tool is the single source of truth the Python seeder and end-to-end
// tests use, so the cloud-side index stays in sync with what the device SDK
// will emit.

#include "fingerprint.hpp"
#include "crypto.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

struct WavData {
    int sample_rate = 0;
    int num_channels = 0;
    int bits_per_sample = 0;
    std::vector<int16_t> samples;  // mono, 16-bit
};

uint32_t read_u32_le(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
           (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

uint16_t read_u16_le(const uint8_t* p) {
    return static_cast<uint16_t>(p[0]) | (static_cast<uint16_t>(p[1]) << 8);
}

bool read_wav(const std::string& path, WavData& out, std::string& err) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        err = "cannot open " + path;
        return false;
    }
    std::vector<uint8_t> buf((std::istreambuf_iterator<char>(in)),
                             std::istreambuf_iterator<char>());
    if (buf.size() < 44 || std::memcmp(&buf[0], "RIFF", 4) != 0 ||
        std::memcmp(&buf[8], "WAVE", 4) != 0) {
        err = "not a RIFF/WAVE file";
        return false;
    }

    size_t pos = 12;
    int fmt_audio_format = 0;
    size_t data_offset = 0;
    size_t data_size = 0;
    while (pos + 8 <= buf.size()) {
        const char* chunk_id = reinterpret_cast<const char*>(&buf[pos]);
        uint32_t chunk_size = read_u32_le(&buf[pos + 4]);
        if (std::memcmp(chunk_id, "fmt ", 4) == 0) {
            if (pos + 8 + 16 > buf.size()) {
                err = "truncated fmt chunk";
                return false;
            }
            fmt_audio_format = read_u16_le(&buf[pos + 8]);
            out.num_channels = read_u16_le(&buf[pos + 10]);
            out.sample_rate = static_cast<int>(read_u32_le(&buf[pos + 12]));
            out.bits_per_sample = read_u16_le(&buf[pos + 22]);
        } else if (std::memcmp(chunk_id, "data", 4) == 0) {
            data_offset = pos + 8;
            data_size = chunk_size;
            break;
        }
        pos += 8 + chunk_size + (chunk_size & 1);  // word-align
    }

    if (data_offset == 0) {
        err = "no data chunk";
        return false;
    }
    if (fmt_audio_format != 1) {
        err = "only PCM format is supported (got format " + std::to_string(fmt_audio_format) + ")";
        return false;
    }
    if (out.bits_per_sample != 16) {
        err = "only 16-bit samples supported (got " + std::to_string(out.bits_per_sample) + ")";
        return false;
    }
    if (data_offset + data_size > buf.size()) {
        data_size = buf.size() - data_offset;  // tolerate truncation
    }

    const size_t bytes_per_sample = 2 * out.num_channels;
    const size_t num_frames = data_size / bytes_per_sample;
    out.samples.reserve(num_frames);
    const uint8_t* data_ptr = &buf[data_offset];
    for (size_t i = 0; i < num_frames; ++i) {
        int32_t mix = 0;
        for (int c = 0; c < out.num_channels; ++c) {
            int16_t s = static_cast<int16_t>(read_u16_le(data_ptr + i * bytes_per_sample + c * 2));
            mix += s;
        }
        mix /= out.num_channels > 0 ? out.num_channels : 1;
        out.samples.push_back(static_cast<int16_t>(std::max(-32768, std::min(32767, mix))));
    }
    return true;
}

std::vector<int16_t> resample_linear(const std::vector<int16_t>& src, int src_rate, int dst_rate) {
    if (src_rate == dst_rate) return src;
    const double ratio = static_cast<double>(src_rate) / static_cast<double>(dst_rate);
    const size_t dst_len = static_cast<size_t>(src.size() / ratio);
    std::vector<int16_t> dst(dst_len);
    for (size_t i = 0; i < dst_len; ++i) {
        const double src_pos = i * ratio;
        const size_t idx = static_cast<size_t>(src_pos);
        const double frac = src_pos - idx;
        const int16_t s0 = src[std::min(idx, src.size() - 1)];
        const int16_t s1 = src[std::min(idx + 1, src.size() - 1)];
        dst[i] = static_cast<int16_t>(s0 + (s1 - s0) * frac);
    }
    return dst;
}

std::string bytes_to_hex(const uint8_t* data, size_t len) {
    static const char* hex_chars = "0123456789abcdef";
    std::string s;
    s.resize(len * 2);
    for (size_t i = 0; i < len; ++i) {
        s[2 * i] = hex_chars[(data[i] >> 4) & 0xF];
        s[2 * i + 1] = hex_chars[data[i] & 0xF];
    }
    return s;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr,
                     "usage: fingerprint_cli <wav> [--window-ms N] [--hop-ms N]\n");
        return 2;
    }
    std::string wav_path = argv[1];
    int window_ms = 3000;
    int hop_ms = 1500;

    for (int i = 2; i + 1 < argc; i += 2) {
        std::string flag = argv[i];
        int value = std::atoi(argv[i + 1]);
        if (flag == "--window-ms") window_ms = value;
        else if (flag == "--hop-ms") hop_ms = value;
        else {
            std::fprintf(stderr, "unknown flag: %s\n", flag.c_str());
            return 2;
        }
    }

    WavData wav;
    std::string err;
    if (!read_wav(wav_path, wav, err)) {
        std::fprintf(stderr, "error: %s\n", err.c_str());
        return 1;
    }

    const int target_rate = 16000;
    std::vector<int16_t> mono16k =
        (wav.sample_rate == target_rate) ? wav.samples
                                         : resample_linear(wav.samples, wav.sample_rate, target_rate);

    const size_t window_samples = (static_cast<size_t>(window_ms) * target_rate) / 1000;
    const size_t hop_samples = (static_cast<size_t>(hop_ms) * target_rate) / 1000;
    if (mono16k.size() < window_samples) {
        std::fprintf(stderr, "audio shorter than window (%zu < %zu samples)\n",
                     mono16k.size(), window_samples);
        return 1;
    }

    acr::FingerprintEngine engine(target_rate, 4096);
    size_t pos = 0;
    int emitted = 0;
    while (pos + window_samples <= mono16k.size()) {
        auto fp = engine.fingerprint(&mono16k[pos], window_samples);
        const int start_ms = static_cast<int>((pos * 1000) / target_rate);
        std::printf("%d %s\n", start_ms, bytes_to_hex(fp.data(), fp.size()).c_str());
        pos += hop_samples;
        ++emitted;
    }

    std::fprintf(stderr, "emitted %d fingerprints from %s (%.2fs, %d Hz)\n", emitted,
                 wav_path.c_str(), mono16k.size() / static_cast<float>(target_rate),
                 target_rate);
    return 0;
}
