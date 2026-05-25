# WinVE Project Roadmap & Guidelines

This document outlines the development roadmap, possible improvement plans, core philosophies, and design rules for WinVE.

---

## Roadmap

### Confirmed Features
- **Local PC Voice Commands (Offline Mode)**
  - Enable local automation controls (e.g., *"lock computer"*, *"open Notepad"*, *"take screenshot"*) that execute locally via shell commands.
  - Support a separate offline mode with its own dedicated wake word and keyboard shortcut/keybind, allowing seamless toggling between local PC control and Home Assistant control.
- **Custom Script Triggers**
  - Enable mapping of voice commands to custom paths or local batch/python scripts in the settings window.

---

## Possible Improvement Plans

### Glassmorphic HUD & Interactive Smart Widgets (UI/UX & Aesthetics)
- **Real-time Transcript Overlay**: Render streaming STT transcriptions and responses in a beautiful, glassmorphic HUD directly on screen.
- **Quick-Action Control Cards**: Display temporary floating cards with sliders/toggles (e.g., brightness or thermostat adjustments) based on intent recognition for immediate manual overrides.
- **Theme Customization Engine**: Settings GUI controls to change overlay themes (Siri Conic, Google Dots, Retro Wave), adjust positioning (HUD, top right, center), and configure background blur opacity.

### Windows System Integration & Audio Ducking Engine (Core System & Performance)
- **Universal Windows Session Ducking**: Automatically reduce system-wide volume (e.g., Spotify, Chrome, games) via native Windows API when listening is triggered, restoring it upon completion.
- **Local Offline TTS Fallback**: Integrate offline TTS (e.g., `pyttsx3` or a compiled `piper` binary) to verbally announce connection dropouts or system warnings without needing Home Assistant.
- **Smart Noise Auto-Calibration**: Ambient noise check on startup to dynamically calibrate silence VAD limits and reduce false-positive wake word events.

### Local Offline PC Control & Satellite Arbitration (Connectivity & Local Automation)
- **Multi-Room Satellite Arbitration**: Coordinate with other network satellites via UDP broadcasts to ensure only the closest satellite (highest VAD score) answers a wake word.

---

## Philosophy of Additions

When proposing or introducing new features to WinVE, development must adhere to the following principles:

1. **Windows-Native First**: Any features added must prioritize and leverage Windows-native APIs (`ctypes`, WASAPI, system registry) rather than generic cross-platform alternatives that add unnecessary runtimes.
2. **Minimal Resource Footprint**: WinVE is designed to run silently in the background. Features must not consume notable CPU cycles when idle. Network requests, animations, and audio streams must be strictly event-driven.
3. **Local Privacy Focus**: Processing must occur locally whenever possible. Wake word analysis is entirely local (via `openWakeWord` ONNX). Features requiring external cloud services are prohibited.
4. **Self-Contained Executable Packaging**: Every feature must be compatible with PyInstaller packaging so that the final executable remains a single, double-clickable, zero-install directory package.

---

## Do-s and Don't-s

### Do-s
- **DO** use `utils.get_env()` and `utils.get_env_bool()` to parse parameters from the configuration file.
- **DO** use `os.environ` updates to propagate settings changes in-process immediately.
- **DO** ensure PyAudio and PyStray resources are cleanly disposed of in the `cleanup()` method.
- **DO** support UTF-8 encoding strings safely across loggers and path management.
- **DO** maintain comprehensive testing coverage by running the full test suite (`py tests/run_tests.py`) before staging commits.
- **DO** keep openWakeWord inference to ONNX (`.onnx` files) for performance and ease of packaging on Windows.

### Don't-s
- **DON'T** introduce heavy cross-platform GUI frameworks (such as Electron or PyQt). Stick to Flet for GUI and styling.
- **DON'T** add or bundle `.tflite` model files in the `models/` folder. They represent legacy Linux code remnants and must be excluded.
- **DON'T** load `.env` variables using `load_dotenv` without specifying `override=True`, as it fails to refresh changed process parameters.
- **DON'T** use hardcoded paths or paths outside the workspace directory structure.
- **DON'T** bypass the `vad.py` speech classifier when streaming audio to Home Assistant, to prevent flooding the server with silent packets.
