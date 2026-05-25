# openWakeWord ONNX Inference on Windows

## Overview
`openWakeWord` is an open-source, ultra-low resource wake word detection framework. While on Linux it sometimes falls back to `tflite_runtime`, on Windows it relies entirely on **ONNX Runtime** for model inference. This provides native hardware acceleration (CPU/DirectML) and simplifies self-contained packaging.

## Core Architecture
openWakeWord operates on windowed, streaming audio inputs.
1. **Audio Framing**: It expects 16kHz, mono, 16-bit PCM audio. Audio is processed in chunks of 1280 samples (representing an 80ms step size).
2. **Feature Extraction**:
   - The raw audio chunk is passed through a Mel-spectrogram generator (producing log-mel spectrogram features).
   - Mel-spectrogram features are normalized and queued.
3. **Inference Pipeline**:
   - A pre-trained neural network (ResNet or MobileNet-style architecture) processes the spectrogram frame-by-frame.
   - For every 80ms chunk, the model outputs a probability value (between `0.0` and `1.0`) indicating the confidence of a wake word being present in the rolling history window.
   - Predictions are smoothed over a short temporal window (typically the last few predictions) to prevent single-frame spikes from triggering false alerts.

## Critical Parameters

### 1. Detection Threshold (`HA_WAKE_WORD_THRESHOLD`)
- **Default**: `0.5`
- **Behavior**: If the smoothed probability of a wake word exceeds this threshold, a trigger is fired.
- **Calibration**: High thresholds (e.g., `0.7` to `0.85`) prevent false positives in noisy rooms but require clearer pronounciation. Low thresholds (e.g., `0.3` to `0.45`) are useful for quiet rooms or if the mic is far away.

### 2. Voice Activity Detection (VAD) Threshold (`HA_WAKE_WORD_VAD_THRESHOLD`)
- **Default**: `0.3`
- **Behavior**: To save CPU, openWakeWord runs a lightweight VAD (using Silero VAD or a simple WebRTC VAD wrapper) before calling the primary neural network. If the VAD probability is lower than this threshold, the frame is skipped as silence/background noise.
- **Calibration**: If set too high, quiet speech won't trigger the VAD, causing the wake word to be ignored. If set to `0.0`, the VAD is bypassed and ONNX inference runs on every single 80ms block, which increases idle CPU usage.

### 3. Noise Suppression
- openWakeWord has built-in support for SpeexDSP-based noise suppression. On Windows, this is optional and depends on compile-time C-bindings. If enabled, it filters background hums (like PC fan noise) before feeding the audio to the spectrogram extractor.

## Performance Profile on Windows
- **CPU Overhead**: Typically < 2-4% CPU on modern processors.
- **Memory Overhead**: 15MB - 35MB RAM depending on the number of active loaded models.
- **Inference Time**: Usually < 10ms per 80ms block.
