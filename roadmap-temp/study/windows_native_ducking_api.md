# Windows Native Audio Ducking APIs

## Overview
Audio Ducking is the process of reducing the volume of active system audio sessions (such as media players, browsers, or games) when a voice assistant is listening, ensuring that the assistant can clearly hear user commands without speaker interference. On Windows, this is achieved using the **Core Audio APIs** via COM interfaces wrapped in `ctypes`.

## Windows Core Audio COM Interfaces
To interact with system audio sessions, Windows provides several Component Object Model (COM) interfaces:
1. **`MMDeviceEnumerator`**: Discovers and enumerates audio endpoint devices (speakers, microphones).
2. **`IMMDevice`**: Represents a specific audio device.
3. **`IAudioSessionManager2`**: Provides access to the audio session control and session enumerator.
4. **`IAudioSessionEnumerator`**: Enumerates all active audio sessions on an endpoint.
5. **`IAudioSessionControl2`**: Retrieves information about a session (such as process ID, state, and name).
6. **`ISimpleAudioVolume`**: Controls the volume and mute state of an individual audio session.

## Implementing Volume Control via ctypes
To avoid external dependencies like `pycaw` in light environments, these COM interfaces can be queried using built-in Python `ctypes` and COM helper definitions.

### 1. Initializing COM Library
Before calling any COM interfaces, the thread must initialize the COM library:
```python
import ctypes
ctypes.windll.ole32.CoInitialize(None)
```

### 2. COM VTable Mapping
COM interfaces are defined by a Virtual Method Table (VTable) — a list of function pointers. To call a COM method, we must look up its index in the VTable.
For example, the `ISimpleAudioVolume` interface contains the following methods:
- `SetMasterVolume` (Index 3)
- `GetMasterVolume` (Index 4)
- `SetMute` (Index 5)
- `GetMute` (Index 6)

### Calling a COM Method in Python
```python
# Helper to call COM methods
def call_com_method(interface_ptr, method_index, *args):
    # Retrieve the VTable address
    vtable_ptr = ctypes.cast(interface_ptr, ctypes.POINTER(ctypes.c_void_p))[0]
    # Get the function pointer at method_index
    fn_ptr = ctypes.cast(vtable_ptr + method_index * ctypes.sizeof(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p))[0]
    # Construct ctypes function
    prototype = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *[type(arg) for arg in args])
    return prototype(fn_ptr)(interface_ptr, *args)
```

## Ducking Implementation Logic
To perform ducking:
1. Obtain the `MMDeviceEnumerator` and retrieve the default playback device.
2. Query `IAudioSessionManager2` from the device.
3. Call `GetSessionEnumerator` to fetch all active audio sessions.
4. Iterate through sessions:
   - Check if the session is active (state == 1).
   - Get the process ID of the session.
   - Ignore WinVE's own process to prevent ducking its own TTS responses.
   - Store the current master volume (using `ISimpleAudioVolume.GetMasterVolume`).
   - Reduce the volume by a factor (e.g., set to `0.2` for 20% volume) using `ISimpleAudioVolume.SetMasterVolume`.
5. Once the voice interaction is complete, restore each session to its original stored volume.

## System-Level Ducking (Windows Native)
Windows also supports automatic system-managed ducking (accessible via Control Panel -> Sound -> Communications Tab). However, this only triggers during active "Communication" style voice calls (like Skype/Teams calls) initiated via the Win32 Telephony API. WinVE implements custom application-level ducking to give the user fine-grained control over which applications get quieted and by how much.
