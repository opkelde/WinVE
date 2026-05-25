# Voice Activity Detection (VAD) Algorithms

## Overview
Voice Activity Detection (VAD) is a technology used to determine whether a given audio frame contains human speech or just silent background noise. For an always-on desktop voice assistant like WinVE, VAD acts as a critical gatekeeper: it prevents silent audio or background noise from being streamed to Home Assistant, saving bandwidth and server CPU cycles.

## Core VAD Approaches

### 1. Energy/RMS Thresholding (Baseline)
- **Mechanism**: Calculates the Root Mean Square (RMS) energy of an audio frame:
  $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} x_i^2}$$
  If the RMS energy exceeds a pre-defined threshold (calibrated above the ambient noise floor), the frame is marked as speech.
- **Pros**: Zero latency, extremely fast, takes virtually no CPU cycles (microsecond execution).
- **Cons**: Cannot differentiate between human voices and non-speech sounds (e.g. keyboard typing, door slams, fan hums, coughing).

### 2. WebRTC VAD (Spectral/Statistical)
- **Mechanism**: Extracts sub-band energies from the audio frame and calculates log-likelihood ratios using Gaussian Mixture Models (GMMs). Originally developed by Google for WebRTC.
- **Pros**: Extremely fast (written in C), highly efficient, low latency (operates on 10, 20, or 30ms frames).
- **Cons**: Sensitive to sudden spikes of high-frequency noise. Has difficulty isolating speech in low signal-to-noise ratio (SNR) environments (e.g., loud music playing).

### 3. Silero VAD (Deep Learning / Neural Networks)
- **Mechanism**: A deep learning model trained on voice samples in over 100 languages. It takes raw audio chunks and outputs a speech probability score.
- **Pros**: Extremely accurate. High resistance to background noises, music, and transient sounds. It rarely triggers on keyboard clicks or household noise.
- **Cons**: Higher CPU overhead than WebRTC/RMS (though still low enough for modern PCs). Requires ONNX runtime or PyTorch.

---

## Comparison Table

| Metric | RMS Thresholding | WebRTC VAD | Silero VAD |
| :--- | :--- | :--- | :--- |
| **Method** | Math/Signal Energy | GMM (Statistical) | CNN/RNN (Neural) |
| **Accuracy** | Low | Moderate | Very High |
| **CPU Overhead** | < 0.01% | < 0.1% | 1.0% - 2.5% |
| **Latency** | None | 10 - 30ms | 30 - 100ms |
| **Dependencies** | None | `webrtcvad` library | ONNX / PyTorch |
| **False Triggers** | High (triggers on clicks) | Moderate (triggers on whistle/hum) | Extremely Low |

---

## Calibration in WinVE
WinVE utilizes a multi-stage approach to VAD:
1. **Local Silence Filter (`vad.py`)**: Uses a simple RMS threshold filter. If the microphone signal energy is below the silence floor, it doesn't even send the frame to openWakeWord, preserving local CPU cycles.
2. **openWakeWord VAD Gate**: openWakeWord has built-in VAD (WebRTC or Silero depending on initialization kwargs). Only if this VAD returns a high probability does it call the heavier ONNX wake word classifiers.
3. **Home Assistant Streaming Gate**: While streaming voice packets to Home Assistant, WinVE continuously checks the VAD state. If the user stops talking for more than a configured duration (e.g., 2.0 seconds of silence), WinVE automatically stops recording and closes the stream, allowing HA to process the request immediately.
