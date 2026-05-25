# PyInstaller Windows Packaging Guide for WinVE

## Overview
WinVE is designed to run as a portable Windows application. PyInstaller is used to package the Python script, its dependencies, DLL runtimes (such as PortAudio, WebView2), and ONNX models into a double-clickable directory (`dist/WinVE/`) or single-file executable.

## PyInstaller Mechanics
PyInstaller analyzes the source code import statements, crawls dependencies, and collects them into a staging area.
- In **one-directory mode** (`--onedir`), PyInstaller creates a folder containing `WinVE.exe` alongside all dependent `.dll` and `.pyd` files. This is preferred for updates and quick launch speeds.
- In **one-file mode** (`--onefile`), PyInstaller bundles everything into a self-extracting executable. On launch, it decompresses its payloads to a temporary folder (`C:\\Users\\<user>\\AppData\\Local\\Temp\\_MEIxxxxxx`) before executing. This causes longer startup delays, which makes `--onedir` the recommended approach for desktop background services.

## Handling Dynamic Assets (ONNX Models & Audio Files)
PyInstaller only copies code files by default. Non-code files (such as sound effects in `sound/`, ONNX models in `models/`, or images in `img/`) must be explicitly declared in the `.spec` file.

### Spec File Configuration
The `WinVE.spec` file controls the build properties:
```python
# WinVE.spec
block_cipher = None

added_data = [
    ('models/*.onnx', 'models'),
    ('sound/*.wav', 'sound'),
    ('img/*.ico', 'img'),
    ('.env.example', '.')
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_data,
    hiddenimports=[
        'openwakeword',
        'onnxruntime',
        'flet.canvas',
        'pyaudio'
    ],
    ...
)
```

## Runtime Path Resolution (Frozen Code)
When packaged, standard relative paths (like `os.path.abspath(__file__)`) point to the temporary extraction directory (`_MEIxxxxxx`) or the directory containing the binary.
To read files correctly in both development mode and frozen execution mode, use the following routing helper:

```python
import sys
import os

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
```

## Critical Windows DLL Dependencies

### 1. PyAudio (PortAudio DLL)
PyAudio binds to `portaudio.dll`. PyInstaller must collect this binary. If it fails, users will receive a `"PyAudio helper DLL not found"` error. Adding `pyaudio` to `hiddenimports` forces PyInstaller's hooks to grab the DLL automatically.

### 2. ONNX Runtime DLLs
ONNX Runtime relies on optimized C++ runtimes (`onnxruntime_providers_shared.dll`, `onnxruntime.dll`). Ensure the environment path contains these folders during compilation so PyInstaller can resolve and copy them.

### 3. Flet and WebView2
Flet displays interfaces using a lightweight browser wrapper (WebView2 on Windows). PyInstaller collects Flet's asset folder containing the Flutter runtimes.
- Setting `--windowed` or `--noconsole` suppresses the background terminal window when launching, leaving only the Flet GUI visible.
- If debugging issues, compile with `--console` (or use `build_console.bat`) to inspect stderr/stdout streams.
