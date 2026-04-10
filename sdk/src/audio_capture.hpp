/**
 * Audio Capture using ALSA
 *
 * Captures PCM audio for fingerprinting in a background thread.
 */

#ifndef ACR_AUDIO_CAPTURE_HPP
#define ACR_AUDIO_CAPTURE_HPP

#include "fingerprint.hpp"

#include <atomic>
#include <condition_variable>
#include <functional>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

typedef struct _snd_pcm snd_pcm_t;

namespace acr {

/**
 * Audio Capture Manager
 *
 * Captures audio from default ALSA device in background thread.
 */
class AudioCapture {
public:
    /**
     * Callback when audio frame is captured
     *
     * @param samples PCM samples (16-bit signed mono)
     * @param num_samples Number of samples
     */
    using FrameCallback = std::function<void(const int16_t* samples, size_t num_samples)>;

    /**
     * Constructor
     *
     * @param sample_rate Audio sample rate (default: 16000)
     * @param capture_duration_ms Duration of each capture in milliseconds (default: 3000)
     * @param capture_interval_sec Interval between captures in seconds (default: 30)
     */
    AudioCapture(int sample_rate = 16000, int capture_duration_ms = 3000,
                 int capture_interval_sec = 30);

    ~AudioCapture();

    /**
     * Initialize audio capture
     *
     * @param callback Function to call when frame is captured
     * @return true if successful
     */
    bool init(FrameCallback callback);

    /**
     * Start capturing audio in background thread
     *
     * @return true if successful
     */
    bool start();

    /**
     * Stop capturing audio
     */
    void stop();

    /**
     * Check if currently capturing
     *
     * @return true if capturing
     */
    bool is_capturing() const;

    /**
     * Get estimated CPU usage percentage
     *
     * @return CPU usage estimate (target < 2%)
     */
    float get_cpu_usage() const;

private:
    int sample_rate_;
    int capture_duration_ms_;
    int capture_interval_sec_;

    snd_pcm_t* pcm_handle_ = nullptr;
    FrameCallback callback_;

    std::atomic<bool> capturing_{false};
    std::atomic<bool> stop_requested_{false};
    std::unique_ptr<std::thread> capture_thread_;

    std::vector<int16_t> audio_buffer_;

    // Performance metrics
    std::atomic<float> cpu_usage_{0.0f};
    std::atomic<int> frame_count_{0};

    /**
     * Background capture thread main loop
     */
    void capture_thread_main();

    /**
     * Open ALSA PCM device
     *
     * @return true if successful
     */
    bool open_pcm_device();

    /**
     * Close ALSA PCM device
     */
    void close_pcm_device();

    /**
     * Capture one frame of audio
     *
     * @return true if successful
     */
    bool capture_frame();

    /**
     * Handle ALSA underrun/overrun
     */
    void handle_pcm_error(int err);
};

}  // namespace acr

#endif /* ACR_AUDIO_CAPTURE_HPP */
