# Local Offline Text-To-Speech (TTS) Engines

## Overview
WinVE is designed to operate offline for local PC controls. When Home Assistant is unreachable, WinVE can announce warnings, errors, or custom script output verbally using local offline Text-to-Speech (TTS) engines. This document evaluates local TTS solutions available on Windows.

## Windows TTS Options

### 1. Windows SAPI5 (via `pyttsx3`)
- **Mechanism**: The Microsoft Speech API (SAPI5) is a legacy COM-based TTS engine built into every version of Windows. In Python, it is accessed using the `pyttsx3` library, which initializes a COM wrapper around `Sapi.SpVoice`.
- **Pros**:
  - **Zero Install**: Requires no downloaded models or external binaries.
  - **Highly Stable**: Works instantly out-of-the-box.
  - **Zero Memory/CPU Overhead**: Negligible footprint.
- **Cons**:
  - **Robotic Voice**: Sound quality is highly artificial (robotic) compared to modern neural voice models.
  - **Limited Customization**: Limited selection of voices (usually Microsoft David, Zira, and Hazel).

### 2. Piper TTS (Neural Engine)
- **Mechanism**: A fast, local neural text-to-speech engine optimized for low-resource hardware (like Raspberry Pis or local desktops). Piper models are exported as ONNX files.
- **Pros**:
  - **Natural Speech**: Sound quality is exceptionally high, resembling modern assistant voices.
  - **Wide Selection**: Hundreds of pre-trained voices and language models are available.
  - **Fast Execution**: Piper can generate audio faster than real-time even on low-spec CPUs.
- **Cons**:
  - **Packaging Overhead**: Requires bundling the Piper executable/library and model files (~15-50MB per voice model), increasing the application installation package size.

### 3. Microsoft WinRT / OneCore Speech Synthesis
- **Mechanism**: A newer, more modern TTS engine built into Windows 10/11 (used by Cortana/Narrator). It can be accessed via Python's `winsdk` bindings.
- **Pros**:
  - **High Quality**: Much more natural and expressive than SAPI5.
  - **Built-in**: Pre-installed on modern Windows 10/11 systems.
- **Cons**:
  - **Complex Bindings**: Requires heavy Windows Runtime (WinRT) bindings (`winsdk` module), which are complex to package with PyInstaller and do not support older Windows versions.

---

## Comparison Summary

| Metric | SAPI5 (pyttsx3) | Piper TTS | WinRT OneCore |
| :--- | :--- | :--- | :--- |
| **Technology** | Concatenative / Formant | Neural Network (ONNX) | Hybrid Concatenative/Neural |
| **Voice Quality** | Robotic | High (Natural) | Medium-High |
| **Download Needed** | None | Yes (Model files) | None |
| **Startup Latency** | < 50ms | ~100-300ms | ~50-100ms |
| **Disk Footprint** | ~0 MB | 15MB - 100MB | ~0 MB |
| **Python Package** | `pyttsx3` (Pure Python) | `piper-tts` or compiled binary | `winsdk` |

---

## Implementation Strategies for WinVE

### Option A: Pure Python SAPI5 Implementation
To avoid adding external binaries to the installation package, WinVE can use SAPI5 via `ctypes` or `pyttsx3` for quick notifications:
```python
import pyttsx3

def speak_offline(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150) # speed
    engine.say(text)
    engine.runAndWait()
```

### Option B: Executable Wrapper for Piper TTS
To achieve premium voice quality:
1. Download a pre-compiled Piper command-line binary.
2. Download a high-quality voice model (e.g. `en_US-lessac-medium.onnx`).
3. Run the generation process in a background thread to prevent UI blocks:
```python
import subprocess
import os

def generate_piper_audio(text, voice_model_path, piper_exe_path, output_wav):
    cmd = [
        piper_exe_path,
        "-m", voice_model_path,
        "-f", output_wav
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
    p.communicate(input=text.encode('utf-8'))
    return p.returncode == 0
```
This WAV file is then played back using `PyAudio` or standard Windows multimedia playsound APIs.
