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
- **Voice Spells Bypass System**
  - Support defining custom phrase "spells" (e.g. *"Lumos"*, *"Nox"*) that bypass the primary wake word entirely to immediately execute specific Home Assistant services or local system scripts. Allow users to add new spells, configure trigger types, toggle them on/off, or remove them dynamically.
- **Settings Configuration Import & Export**
  - Allow users to export their complete WinVE configuration (environment settings, custom script mappings, spells list) to a portable backup file, and import it back with integrity validation and automatic process environment updates.
- **Suppress Screen Text with Fullscreen Applications**
  - Add a settings toggle to automatically hide listening HUD animations, overlays, and response texts when a DirectX game or other fullscreen application is actively running in the foreground to prevent visual interference.

---

## Possible Improvement Plans

### Glassmorphic HUD & Interactive Smart Widgets (UI/UX & Aesthetics)
- **Real-time Transcript Overlay**: Render streaming STT transcriptions and responses in a beautiful, glassmorphic HUD directly on screen.
- **Quick-Action Control Cards**: Display temporary floating cards with sliders/toggles (e.g., brightness or thermostat adjustments) based on intent recognition for immediate manual overrides.
- **Theme Customization Engine**: Settings GUI controls to change overlay themes (Siri Conic, Google Dots, Retro Wave), adjust positioning (HUD, top right, center), and configure background blur opacity.
- **LED Light Ring Simulator**: Render smart-speaker style circular LED animations (spinning, breathing, pulsing) directly on the screen HUD to represent the listener's active state.
- **Transparent Keyboard Chat Overlay**: A transparent text-based input HUD bar that allows typing commands using keyboard hotkeys when voice input is not preferred.
- **Smart Home Floating Widget**: A compact home automation dashboard card overlay showing state indicators and quick toggles.

### Windows System Integration & Audio Ducking Engine (Core System & Performance)
- **Universal Windows Session Ducking**: Automatically reduce system-wide volume (e.g., Spotify, Chrome, games) via native Windows API when listening is triggered, restoring it upon completion.
- **Local Audio Caching**: Pre-cache text-to-speech audio outputs and voice triggers locally to reduce repeated network delays and minimize server requests.
- **Local Offline TTS Fallback**: Integrate offline TTS (e.g., `pyttsx3` or a compiled `piper` binary) to verbally announce connection dropouts or system warnings without needing Home Assistant.
- **Push-To-Talk Keyboard Mode**: Listen continuously only while holding a configured hotkey down, muting immediately when the key is released.
- **Smart Noise Auto-Calibration**: Ambient noise check on startup to dynamically calibrate silence VAD limits and reduce false-positive wake word events.
- **Low-Latency SoundPool Manager**: Cache small system feedback sound files (beeps, success ticks, error alerts) directly in memory to play them instantly without filesystem access latency.
- **Battery Power Saver**: Monitor Windows battery/power state and automatically throttle sample rates or sleep intervals to preserve battery when unplugged.

### Connectivity, Networking & Diagnostics (Core System & Satellite Management)
- **Multi-Room Satellite Arbitration**: Coordinate with other network satellites via UDP broadcasts to ensure only the closest satellite (highest VAD score) answers a wake word.
- **SSL/TLS Satellite Connection**: Secure local websocket and socket connections between WinVE satellites and Home Assistant using TLS wrappers.
- **mDNS ZeroConf Discovery**: Scan the local area network using multicast DNS to locate and dynamically pair other WinVE nodes without requiring manual IP entries.
- **Diagnostic Web Admin Dashboard**: Run a lightweight local HTTP server displaying diagnostic telemetry, logs, and current configuration settings.
- **Windows Native PC Telemetry Reporting**: Report system diagnostics (CPU load, memory load, active foreground window title, locked/unlocked state) back to Home Assistant.

### Model Calibration, Recovery & Local Parsing (Tuning & Resiliency)
- **Dynamic HA Pipeline Hot-Swapper**: Swaps the target Home Assistant voice pipeline dynamically based on voice commands (e.g., "switch to high quality voice").
- **Voice Profile Pitch Analyzer**: A microphone calibration utility that measures the user's pitch and speaking frequencies to tailor voice activity detection (VAD) thresholds.
- **Custom Wake Word Downloader**: An in-app utility to download pre-trained wake word ONNX models from community libraries directly into the `models/` folder.
- **Wake Word False-Alarm Logger**: Record audio buffers around wake word events to analyze and log model confidence, helping users tune detection thresholds.
- **Offline Text-to-Intent Routing**: Fallback local regex-based parser that executes basic media keys, system volume control, and app launching without internet access.
- **Automatic Crash Recovery Daemon**: Watchdog helper process that monitors the main application state and automatically restarts the client in case of unexpected memory or socket errors.
- **Voice Biometrics for Speaker Identification**: Enroll multiple authorized voices locally (extracting vocal signatures) and verify speaker identity using acoustic models, preventing unauthorized users from triggering sensitive PC actions or home automation commands.

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
