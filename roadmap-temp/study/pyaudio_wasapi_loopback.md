# PyAudio and WASAPI Loopback on Windows

## Overview
WinVE captures microphone audio for voice commands and wake word detection. PyAudio, a Python binding for the cross-platform PortAudio library, is used to access Windows audio endpoints. Understanding how Windows audio APIs interact with PyAudio is crucial for low-latency recording and advanced features like WASAPI loopback.

## Windows Audio Drivers & Host APIs
Windows supports several host APIs to communicate with audio hardware. In PyAudio, these are represented as constants:
1. **MME (Multimedia Extensions)**: Legacy, highest latency (~100-200ms), but universally supported.
2. **DirectSound**: DirectX audio API, moderate latency (~50-100ms).
3. **WASAPI (Windows Audio Session API)**: Modern standard, low latency (~10-30ms).
4. **ASIO (Audio Stream Input/Output)**: Professional audio driver, bypasses OS mixers, lowest latency, but requires hardware-specific drivers.

For WinVE, **WASAPI** is the preferred host API because it offers the best balance of low latency, stable mixing, and native OS features.

## PyAudio Device Selection
Each input and output endpoint has a device index. To record audio, PyAudio needs the index of the default or desired microphone.

```python
import pyaudio

p = pyaudio.PyAudio()

# Find WASAPI Host API Index
wasapi_api_index = None
for i in range(p.get_host_api_count()):
    api_info = p.get_host_api_info_by_index(i)
    if api_info.get('name') == 'Windows WASAPI':
        wasapi_api_index = api_info.get('index')
        break

# Get WASAPI Devices
default_mic_index = p.get_default_input_device_info()['index']
```

## WASAPI Loopback (Recording System Audio)
WASAPI Loopback allows capturing the audio being output to speakers or headphones (e.g., to analyze game sound, system events, or media streams). 
- In WASAPI, loopback devices are registered as input devices but have `maxInputChannels == 0` and `maxOutputChannels > 0` in their default profiles.
- To record from a loopback device, you must open an input stream on that device's index, specifying the sample rate of the output device (typically 44100Hz or 48000Hz) and using WASAPI-specific stream flags.

```python
# Open WASAPI Loopback Stream
stream = p.open(
    format=pyaudio.paInt16,
    channels=2,
    rate=48000,
    input=True,
    input_device_index=loopback_device_index,
    frames_per_buffer=1024
)
```

## Sample Rate Conversion (Downsampling)
Most hardware runs at 44.1kHz or 48kHz. However, wake word engines (like openWakeWord/microWakeWord) and speech-to-text engines require **16kHz mono audio**.
- Recording directly at 16kHz relies on PortAudio's built-in resampler or Windows MME drivers, which can introduce artifacts, distortion, or performance overhead.
- **Recommended Approach**: Record at the device's native rate (e.g. 48kHz, 1 channel) and perform digital downsampling in Python using NumPy slice/averaging or a fast FIR/IIR filter to reduce high-frequency aliasing before feeding the frames to openWakeWord.

### Simple Downsampling Example (Decimation)
To downsample from 48kHz to 16kHz, decimate by a factor of 3:
```python
import numpy as np

def downsample_3x(audio_48k):
    # Take every 3rd sample
    return audio_48k[::3]
```
*(Note: Decimation without a low-pass filter can cause aliasing, but for wake word detection, simple decimation is often sufficiently accurate and consumes very little CPU).*
