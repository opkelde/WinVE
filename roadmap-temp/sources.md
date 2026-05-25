# WinVE Research Sources & References

This file compiles links, official documentation, and academic/open-source repositories relevant to the development, tuning, and packaging of WinVE.

---

## Wake Word Detection & ONNX Inference

- **[openWakeWord Repository](https://github.com/dscripka/openWakeWord)**
  - *Description*: The foundational repository for openWakeWord. Includes instructions on model structures, custom model training, and dynamic threshold calibrations.
- **[ONNX Runtime Documentation](https://onnxruntime.ai/docs/)**
  - *Description*: Developer guides for deploying machine learning models using ONNX Runtime. Details quantization configurations (FP32 to INT8) and CPU/DirectML optimization threads.
- **[Silero VAD Repository](https://github.com/snakers4/silero-vad)**
  - *Description*: High-accuracy pre-trained voice activity detector. Useful for calibrating silence-detection thresholds.

---

## Windows System Integration & Audio Controls

- **[Windows Core Audio APIs (Microsoft Learn)](https://learn.microsoft.com/en-us/windows/win32/coreaudio/core-audio-apis-in-windows-vista)**
  - *Description*: Developer documentation for low-level multimedia audio session controls, endpoints, and volume ducking hooks.
- **[Pycaw Repository](https://github.com/AndreMiras/pycaw)**
  - *Description*: Python Windows Audio Control Library wrapper. Demonstrates direct COM calls via `ctypes` for volume adjustment.
- **[PyAudio / PortAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/)**
  - *Description*: Reference manual for PyAudio. Useful for managing raw recording chunks, WASAPI loopback streams, and input device indices.

---

## GUI Framework & HUD Overlays

- **[Flet Developer Documentation](https://flet.dev/docs/)**
  - *Description*: Documentation for the Flet (Flutter-based) framework. Includes instructions for managing async controls, canvas draws, and transparent window overlays.
- **[Flutter Canvas Shape Drawing Reference](https://api.flutter.dev/flutter/rendering/Canvas-class.html)**
  - *Description*: Detailed API guide for canvas graphics, coordinate transformations, and rendering shapes for animations.

---

## Home Assistant & Voice Assistant Protocols

- **[Home Assistant Voice Control Pipeline](https://www.home-assistant.io/voice-control/)**
  - *Description*: Architectural overview of Home Assistant's Voice Assistant systems (STT, TTS, Intents).
- **[Wyoming Protocol Specification](https://github.com/home-assistant/wyoming)**
  - *Description*: Details the Wyoming TCP Protocol used to communicate with Home Assistant's voice pipelines.
- **[ESPHome Voice Assistant API Reference](https://esphome.io/components/voice_assistant.html)**
  - *Description*: Schema descriptions for the TCP handshake and UDP audio packets exchanged during voice assistant sessions.

---

## Packaging & Distribution

- **[PyInstaller Documentation](https://pyinstaller.org/en/stable/)**
  - *Description*: Packaging manuals detailing runtime path resolution, hidden imports, spec file management, and compiling multi-DLL binaries into portable directories.
