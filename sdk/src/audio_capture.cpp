/**
 * Audio Capture Implementation using ALSA
 */

#include "audio_capture.hpp"

#include <alsa/asoundlib.h>
#include <chrono>
#include <cstring>
#include <iostream>

namespace acr {

AudioCapture::AudioCapture(int sample_rate, int capture_duration_ms,
                           int capture_interval_sec)
    : sample_rate_(sample_rate),
      capture_duration_ms_(capture_duration_ms),
      capture_interval_sec_(capture_interval_sec) {
    int num_samples = (sample_rate * capture_duration_ms) / 1000;
    audio_buffer_.resize(num_samples);
}

AudioCapture::~AudioCapture() {
    stop();
    close_pcm_device();
}

bool AudioCapture::open_pcm_device() {
    int err;

    // Try opening default device
    const char* device = "default";
    err = snd_pcm_open(&pcm_handle_, device, SND_PCM_STREAM_CAPTURE, 0);

    if (err < 0) {
        std::cerr << "ACR: Cannot open audio device: " << snd_strerror(err)
                  << std::endl;
        return false;
    }

    // Allocate hardware parameters
    snd_pcm_hw_params_t* hw_params;
    snd_pcm_hw_params_malloc(&hw_params);

    if ((err = snd_pcm_hw_params_any(pcm_handle_, hw_params)) < 0) {
        std::cerr << "ACR: Cannot initialize hardware parameter structure: "
                  << snd_strerror(err) << std::endl;
        snd_pcm_hw_params_free(hw_params);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
        return false;
    }

    // Set interleaved access mode
    if ((err = snd_pcm_hw_params_set_access(pcm_handle_, hw_params,
                                             SND_PCM_ACCESS_RW_INTERLEAVED)) < 0) {
        std::cerr << "ACR: Cannot set access type: " << snd_strerror(err)
                  << std::endl;
        snd_pcm_hw_params_free(hw_params);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
        return false;
    }

    // Set sample format (16-bit signed)
    if ((err = snd_pcm_hw_params_set_format(pcm_handle_, hw_params,
                                             SND_PCM_FORMAT_S16_LE)) < 0) {
        std::cerr << "ACR: Cannot set sample format: " << snd_strerror(err)
                  << std::endl;
        snd_pcm_hw_params_free(hw_params);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
        return false;
    }

    // Set channels (mono)
    if ((err = snd_pcm_hw_params_set_channels(pcm_handle_, hw_params, 1)) < 0) {
        std::cerr << "ACR: Cannot set channels: " << snd_strerror(err) << std::endl;
        snd_pcm_hw_params_free(hw_params);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
        return false;
    }

    // Set sample rate
    unsigned int actual_rate = sample_rate_;
    if ((err = snd_pcm_hw_params_set_rate_near(pcm_handle_, hw_params,
                                                &actual_rate, nullptr)) < 0) {
        std::cerr << "ACR: Cannot set sample rate: " << snd_strerror(err)
                  << std::endl;
        snd_pcm_hw_params_free(hw_params);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
        return false;
    }

    if (actual_rate != (unsigned int)sample_rate_) {
        std::cerr << "ACR: Sample rate adjusted from " << sample_rate_ << " to "
                  << actual_rate << std::endl;
    }

    // Apply hardware parameters
    if ((err = snd_pcm_hw_params(pcm_handle_, hw_params)) < 0) {
        std::cerr << "ACR: Cannot apply hardware parameters: " << snd_strerror(err)
                  << std::endl;
        snd_pcm_hw_params_free(hw_params);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
        return false;
    }

    snd_pcm_hw_params_free(hw_params);

    // Prepare the PCM device
    if ((err = snd_pcm_prepare(pcm_handle_)) < 0) {
        std::cerr << "ACR: Cannot prepare audio interface: " << snd_strerror(err)
                  << std::endl;
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
        return false;
    }

    return true;
}

void AudioCapture::close_pcm_device() {
    if (pcm_handle_) {
        snd_pcm_drop(pcm_handle_);
        snd_pcm_close(pcm_handle_);
        pcm_handle_ = nullptr;
    }
}

void AudioCapture::handle_pcm_error(int err) {
    if (err == -EPIPE) {
        // UNDERRUN
        std::cerr << "ACR: Audio buffer underrun" << std::endl;
        snd_pcm_prepare(pcm_handle_);
    } else if (err == -ESTRPIPE) {
        // Suspended
        std::cerr << "ACR: Audio device suspended" << std::endl;
        while ((err = snd_pcm_resume(pcm_handle_)) == -EAGAIN) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        if (err < 0) {
            snd_pcm_prepare(pcm_handle_);
        }
    }
}

bool AudioCapture::capture_frame() {
    if (!pcm_handle_) {
        return false;
    }

    int num_samples = audio_buffer_.size();
    snd_pcm_sframes_t frames_read = 0;

    while (frames_read < num_samples) {
        snd_pcm_sframes_t ret = snd_pcm_readi(
            pcm_handle_, audio_buffer_.data() + frames_read,
            num_samples - frames_read);

        if (ret < 0) {
            handle_pcm_error(ret);
            return false;
        }

        if (ret == 0) {
            break;
        }

        frames_read += ret;
    }

    return frames_read == num_samples;
}

bool AudioCapture::init(FrameCallback callback) {
    callback_ = callback;

    if (!open_pcm_device()) {
        return false;
    }

    return true;
}

bool AudioCapture::start() {
    if (capturing_) {
        return true;
    }

    stop_requested_ = false;
    capturing_ = true;

    capture_thread_ = std::make_unique<std::thread>(&AudioCapture::capture_thread_main, this);

    return true;
}

void AudioCapture::stop() {
    if (!capturing_) {
        return;
    }

    stop_requested_ = true;

    if (capture_thread_ && capture_thread_->joinable()) {
        capture_thread_->join();
    }

    capturing_ = false;
}

bool AudioCapture::is_capturing() const {
    return capturing_;
}

float AudioCapture::get_cpu_usage() const {
    return cpu_usage_;
}

void AudioCapture::capture_thread_main() {
    while (!stop_requested_) {
        auto start_time = std::chrono::high_resolution_clock::now();

        // Capture audio frame
        if (capture_frame() && callback_) {
            callback_(audio_buffer_.data(), audio_buffer_.size());
            frame_count_++;
        }

        auto end_time = std::chrono::high_resolution_clock::now();
        auto capture_duration = std::chrono::duration_cast<std::chrono::milliseconds>(
            end_time - start_time);

        // Calculate CPU usage
        float capture_percent =
            (float)capture_duration.count() / (float)capture_duration_ms_;
        cpu_usage_ = capture_percent * 100.0f;

        // Wait for next capture interval
        int remaining_ms = capture_interval_sec_ * 1000 - capture_duration.count();

        if (remaining_ms > 0) {
            std::this_thread::sleep_for(
                std::chrono::milliseconds(remaining_ms));
        }
    }
}

}  // namespace acr
