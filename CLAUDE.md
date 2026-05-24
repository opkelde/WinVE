# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
py main.py                        # Run the main application
```

### Testing
```bash
py tests/run_tests.py             # Run all tests with comprehensive test runner
py tests/run_tests.py --unit-only            # Run only unit tests
py tests/run_tests.py --integration-only     # Run only integration tests  
py tests/run_tests.py --coverage             # Run with coverage report
py tests/run_tests.py --parallel             # Run tests in parallel
py tests/run_tests.py --html                 # Generate HTML report
py tests/run_tests.py --test-file test_utils.py  # Run specific test file

# Individual test modules
py -m pytest -c tests/pytest.ini tests/test_utils.py -v
py -m pytest -c tests/pytest.ini tests/test_audio.py -v
py -m pytest -c tests/pytest.ini tests/test_client.py -v
```

### Building (Windows)
```bash
build.bat                         # Build Windows executable (requires virtual environment)
build_console.bat                 # Build console version with debug output
```

### Dependencies
```bash
pip install -r requirements.txt   # Install main dependencies
pip install -r tests/requirements-test.txt  # Install test dependencies
```

## Architecture Overview

WinVE is a desktop voice assistant for Home Assistant with the following key architectural components:

### Core Components
- **main.py** - Application entry point with HAAssistApp class, handles GUI lifecycle, tray integration, and component orchestration
- **client.py** - HomeAssistantClient handles WebSocket communication with Home Assistant, pipeline management, and audio streaming
- **audio.py** - AudioManager manages microphone input, audio processing, and integrates with VAD for speech detection
- **animation_server.py** - WebSocket server that serves visual animations to the Three.js frontend via browser integration
- **wake_word_detector.py** - Handles wake word detection using OpenWakeWord models with ONNX runtime

### Supporting Modules
- **vad.py** - Voice Activity Detection using WebRTC VAD for smart speech detection
- **utils.py** - Shared utilities for configuration, logging, and audio validation
- **platform_utils.py** - Platform-specific functionality for Windows (Linux support has been removed)
- **flet_settings.py** - Settings GUI for configuration management

### Frontend Integration
- **frontend/index.html** - Siri-style CSS conic-gradient border overlay visual interface with FFT audio analysis
- **sound/** - Audio feedback files (activation.wav, deactivation.wav)
- **models/** - OpenWakeWord ONNX model files for wake word detection

### Key Architectural Patterns

**Event-Driven Architecture**: The application uses WebSocket connections for real-time communication between Home Assistant, the animation server, and the frontend.

**Component Lifecycle**: Main app orchestrates initialization order: audio setup → Home Assistant connection → animation server → wake word detection → tray integration.

**Windows Native Design**: The application is tailored specifically for Windows desktop environments, removing Linux-specific paths.

**Audio Pipeline**: Audio flows from microphone → VAD → wake word detection → Home Assistant STT → TTS response playback, with parallel animation updates.

**Configuration Management**: Environment-based configuration (.env file) with validation and defaults, managed through utils.py.

## Development Notes

### Wake Word Models
- Models stored in `models/` directory as ONNX files
- Configuration via `HA_WAKE_WORD_MODELS` environment variable (comma-separated)
- Custom models can be trained using provided Google Colab notebooks and converted from TFLite to ONNX

### Animation System
- Animations can be disabled via `HA_ANIMATIONS_ENABLED=false` to use DummyAnimationServer
- WebSocket communication on port 8765 (configurable via `ANIMATION_PORT`)
- Real-time audio visualization using FFT analysis in the frontend overlay

### Audio Configuration
- WebRTC VAD with configurable sensitivity (HA_VAD_MODE: 0-3)
- Frame duration and sample rate configurable for different hardware
- Microphone enumeration and selection available through AudioManager

### Home Assistant Integration
- Automatic pipeline discovery and caching
- Support for custom pipeline selection via HA_PIPELINE_ID
- Real-time STT/TTS streaming with binary audio handling

### Build System
- PyInstaller-based builds for Windows distribution
- Inno Setup integration for installer creation
- Virtual environment requirement with dependency bundling