#include "fingerprint.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace acr {

namespace {

constexpr double kPi = 3.14159265358979323846;

// 257 log-spaced frequency bands across the speech-relevant range. 257 edges
// → 256 bit positions in the output fingerprint.
constexpr int kBands = 257;

// FFT scratch size. 4096 samples @ 16 kHz = 256 ms per frame, giving 2048
// positive-frequency bins at ~3.9 Hz resolution.
constexpr int kFft = 4096;

int reverse_bits(int x, int log2n) {
    int n = 0;
    for (int i = 0; i < log2n; ++i) {
        n = (n << 1) | (x & 1);
        x >>= 1;
    }
    return n;
}

int int_log2(int n) {
    int log = 0;
    while ((1 << log) < n) ++log;
    return log;
}

void fft_inplace(std::vector<float>& re, std::vector<float>& im) {
    const int n = static_cast<int>(re.size());
    const int log2n = int_log2(n);

    for (int i = 0; i < n; ++i) {
        int j = reverse_bits(i, log2n);
        if (j > i) {
            std::swap(re[i], re[j]);
            std::swap(im[i], im[j]);
        }
    }

    for (int s = 1; s <= log2n; ++s) {
        const int m = 1 << s;
        const int m_half = m >> 1;
        const double theta = -2.0 * kPi / m;
        const float wm_re = static_cast<float>(std::cos(theta));
        const float wm_im = static_cast<float>(std::sin(theta));

        for (int k = 0; k < n; k += m) {
            float w_re = 1.0f;
            float w_im = 0.0f;
            for (int j = 0; j < m_half; ++j) {
                const int t_idx = k + j + m_half;
                const int u_idx = k + j;
                const float t_re = w_re * re[t_idx] - w_im * im[t_idx];
                const float t_im = w_re * im[t_idx] + w_im * re[t_idx];
                const float u_re = re[u_idx];
                const float u_im = im[u_idx];

                re[u_idx] = u_re + t_re;
                im[u_idx] = u_im + t_im;
                re[t_idx] = u_re - t_re;
                im[t_idx] = u_im - t_im;

                const float nw_re = w_re * wm_re - w_im * wm_im;
                const float nw_im = w_re * wm_im + w_im * wm_re;
                w_re = nw_re;
                w_im = nw_im;
            }
        }
    }
}

std::array<int, kBands> build_band_edges(int fft_size, int sample_rate) {
    // Log-spaced edges across 200 Hz..4000 Hz. This range covers most
    // broadcast audio energy (voice + music fundamentals) while avoiding the
    // parts of the spectrum that degrade fast under HDMI ARC re-encoding.
    const double f_min = 200.0;
    const double f_max = std::min(4000.0, sample_rate / 2.0 - 1.0);
    const double log_min = std::log(f_min);
    const double log_max = std::log(f_max);
    std::array<int, kBands> edges{};
    for (int i = 0; i < kBands; ++i) {
        const double freq = std::exp(log_min + (log_max - log_min) * i / (kBands - 1));
        int bin = static_cast<int>(freq * fft_size / sample_rate);
        if (bin < 1) bin = 1;
        if (bin >= fft_size / 2) bin = fft_size / 2 - 1;
        edges[i] = bin;
    }
    return edges;
}

}  // namespace

FingerprintEngine::FingerprintEngine(int sample_rate, int fft_size)
    : sample_rate_(sample_rate),
      fft_size_(fft_size),
      hop_size_(fft_size / 2) {
    if ((fft_size & (fft_size - 1)) != 0) {
        throw std::invalid_argument("fft_size must be a power of 2");
    }
    fft_input_.assign(fft_size_, 0.0f);
    fft_output_real_.assign(fft_size_, 0.0f);
    fft_output_imag_.assign(fft_size_, 0.0f);
}

FingerprintEngine::~FingerprintEngine() = default;

void FingerprintEngine::apply_hann_window(float* signal, int len) {
    for (int i = 0; i < len; ++i) {
        const float w = 0.5f * (1.0f - std::cos(2.0f * static_cast<float>(kPi) * i / (len - 1)));
        signal[i] *= w;
    }
}

void FingerprintEngine::compute_fft(const float* input, float* out_real, float* out_imag) {
    std::vector<float> re(fft_size_);
    std::vector<float> im(fft_size_, 0.0f);
    for (int i = 0; i < fft_size_; ++i) {
        re[i] = input[i];
    }
    fft_inplace(re, im);
    for (int i = 0; i < fft_size_; ++i) {
        out_real[i] = re[i];
        out_imag[i] = im[i];
    }
}

void FingerprintEngine::compute_magnitude(const float* real, const float* imag, float* magnitude,
                                          int len) {
    for (int i = 0; i < len; ++i) {
        magnitude[i] = std::sqrt(real[i] * real[i] + imag[i] * imag[i]);
    }
}

// Average log-magnitude spectrum across all frames in the window, then
// produce 256 bits from adjacent-band log-energy signs. Averaging makes the
// fingerprint shift-invariant at small time offsets (< window length) — the
// property ACR needs so that devices capturing a broadcast at any phase
// still land in the same hash neighborhood as the seeded reference.
Fingerprint FingerprintEngine::fingerprint(const int16_t* pcm_data, size_t num_samples) {
    Fingerprint out{};
    out.fill(0);

    if (num_samples < static_cast<size_t>(fft_size_)) {
        return out;
    }

    const auto edges = build_band_edges(fft_size_, sample_rate_);
    std::array<double, kBands> band_energy{};
    band_energy.fill(0.0);
    int num_frames = 0;

    std::vector<float> re(fft_size_);
    std::vector<float> im(fft_size_);
    std::vector<float> mag(fft_size_ / 2);

    for (size_t pos = 0; pos + fft_size_ <= num_samples; pos += hop_size_) {
        for (int i = 0; i < fft_size_; ++i) {
            fft_input_[i] = static_cast<float>(pcm_data[pos + i]) / 32768.0f;
        }
        apply_hann_window(fft_input_.data(), fft_size_);
        compute_fft(fft_input_.data(), re.data(), im.data());
        compute_magnitude(re.data(), im.data(), mag.data(), fft_size_ / 2);

        for (int b = 0; b + 1 < kBands; ++b) {
            float energy = 0.0f;
            for (int k = edges[b]; k < edges[b + 1]; ++k) {
                energy += mag[k] * mag[k];
            }
            band_energy[b] += std::log(energy + 1e-9f);
        }
        ++num_frames;
    }

    if (num_frames == 0) {
        return out;
    }
    for (int b = 0; b < kBands; ++b) {
        band_energy[b] /= num_frames;
    }

    // 256 bits: bit i is 1 iff the averaged log-energy in band i is greater
    // than in band i+1. This captures the spectral envelope's shape while
    // throwing away absolute energy (volume-invariant) and phase
    // (shift-invariant).
    for (int i = 0; i < 256; ++i) {
        const bool set = band_energy[i] > band_energy[i + 1];
        if (set) {
            out[i / 8] |= static_cast<uint8_t>(1u << (7 - (i % 8)));
        }
    }

    return out;
}

int FingerprintEngine::fingerprint_distance(const Fingerprint& fp1, const Fingerprint& fp2) {
    int distance = 0;
    for (size_t i = 0; i < fp1.size(); ++i) {
        uint8_t x = fp1[i] ^ fp2[i];
        while (x) {
            x &= x - 1;
            ++distance;
        }
    }
    return distance;
}

std::vector<SpectralPeak> FingerprintEngine::extract_peaks(const float* magnitude, int num_bins,
                                                            int num_frames) {
    std::vector<SpectralPeak> peaks;
    for (int t = 1; t < num_frames - 1; ++t) {
        for (int f = 1; f < num_bins - 1; ++f) {
            const int idx = t * num_bins + f;
            const float center = magnitude[idx];
            if (center > magnitude[idx - 1] && center > magnitude[idx + 1] &&
                center > magnitude[idx - num_bins] && center > magnitude[idx + num_bins]) {
                peaks.push_back({static_cast<uint16_t>(f), static_cast<uint16_t>(t), center});
            }
        }
    }
    std::sort(peaks.begin(), peaks.end());
    if (peaks.size() > 64) peaks.resize(64);
    return peaks;
}

Fingerprint FingerprintEngine::hash_peaks(const std::vector<SpectralPeak>& peaks) {
    Fingerprint out{};
    out.fill(0);
    for (size_t i = 0; i + 1 < peaks.size() && i < 32; ++i) {
        const auto& p1 = peaks[i];
        const auto& p2 = peaks[i + 1];
        const uint32_t anchor = (static_cast<uint32_t>(p1.freq_bin) << 16) |
                                (static_cast<uint32_t>(p2.freq_bin - p1.freq_bin) & 0xFFFF);
        out[i] = static_cast<uint8_t>(anchor & 0xFF) ^ static_cast<uint8_t>((anchor >> 8) & 0xFF);
    }
    return out;
}

}  // namespace acr
