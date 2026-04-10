/**
 * Audio Fingerprinting Engine
 *
 * Implements spectral peak-based fingerprinting using FFT analysis.
 * Algorithm inspired by Shazam/Dejavu approach.
 */

#ifndef ACR_FINGERPRINT_HPP
#define ACR_FINGERPRINT_HPP

#include <array>
#include <cstdint>
#include <vector>

namespace acr {

/**
 * Audio Fingerprint - 256-bit hash
 */
using Fingerprint = std::array<uint8_t, 32>;

/**
 * Spectral Peak - (frequency_bin, time_frame, amplitude)
 */
struct SpectralPeak {
    uint16_t freq_bin;
    uint16_t time_frame;
    float amplitude;

    bool operator<(const SpectralPeak& other) const {
        return amplitude > other.amplitude;  // Sort by amplitude descending
    }
};

/**
 * Fingerprinting Engine
 *
 * Processes raw PCM audio and generates content fingerprints.
 */
class FingerprintEngine {
public:
    /**
     * Constructor
     *
     * @param sample_rate Sample rate in Hz (default: 16000)
     * @param fft_size FFT window size in samples (default: 4096)
     */
    FingerprintEngine(int sample_rate = 16000, int fft_size = 4096);

    ~FingerprintEngine();

    /**
     * Generate fingerprint from raw PCM audio
     *
     * @param pcm_data Raw PCM audio (16-bit signed mono)
     * @param num_samples Number of samples
     * @return 256-bit fingerprint hash
     */
    Fingerprint fingerprint(const int16_t* pcm_data, size_t num_samples);

    /**
     * Compute Hamming distance between two fingerprints
     *
     * @param fp1 First fingerprint
     * @param fp2 Second fingerprint
     * @return Hamming distance (0-256)
     */
    static int fingerprint_distance(const Fingerprint& fp1, const Fingerprint& fp2);

private:
    int sample_rate_;
    int fft_size_;
    int hop_size_;

    // FFT buffers
    std::vector<float> fft_input_;
    std::vector<float> fft_output_real_;
    std::vector<float> fft_output_imag_;

    /**
     * Apply Hann window to signal
     */
    void apply_hann_window(float* signal, int len);

    /**
     * Compute FFT using Cooley-Tukey DFT
     */
    void compute_fft(const float* input, float* out_real, float* out_imag);

    /**
     * Extract spectral peaks from magnitude spectrum
     */
    std::vector<SpectralPeak> extract_peaks(const float* magnitude, int num_bins,
                                             int num_frames);

    /**
     * Generate hash from top peaks
     */
    Fingerprint hash_peaks(const std::vector<SpectralPeak>& peaks);

    /**
     * Compute magnitude spectrum from FFT output
     */
    void compute_magnitude(const float* real, const float* imag, float* magnitude,
                          int len);
};

}  // namespace acr

#endif /* ACR_FINGERPRINT_HPP */
