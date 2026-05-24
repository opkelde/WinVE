# WinVE (Windows Voice Endpoint)

WinVE is a lightweight, high-performance Windows desktop voice satellite endpoint for Home Assistant. It runs as a native ESPHome voice satellite, allowing you to use your PC's microphone and speakers as a native voice assistant endpoint with full support for timers, follow-up conversation modes, and media player ducking.

Featuring a premium, borderless Siri-style glowing visual feedback overlay that reacts dynamically to your voice volume, WinVE is designed to be completely unobtrusive — showing absolutely no screen artifacts when idle, and appearing as a stunning rotating gradient border only when active.

## 🚀 Key Features

- **Native ESPHome Satellite Protocol** — Connects directly to Home Assistant as an ESPHome voice satellite with auto-discovery via mDNS.
- **Siri-Style Glowing Border Overlay** — A fullscreen, transparent, click-through border that glows and rotates with a Siri-style color palette (blue/purple/magenta) during activation, turning cyan/blue on success, red on error, and fading out completely when idle.
- **Audio-Reactive Border** — The thickness and blur intensity of the glowing border scale dynamically in real time based on your voice volume.
- **Wake Word Detection** — Built-in openWakeWord support with pre-trained models (e.g., Alexa, Jarvis, Computer) running locally on your CPU.
- **WebRTC VAD** — High-quality voice activity detection to start/stop listening accurately.
- **Flet-Based Settings UI** — A modern settings window to configure audio devices, wake words, thresholds, and optional Home Assistant integrations.
- **System Tray Integration** — Runs completely in the background within the Windows system tray.
- **Media Player Volume Management** — Automatically ducks and restores the volume of configured Home Assistant media players when you start speaking.
- **Interactive Prompts Support** — Accepts incoming prompts from Home Assistant via its HTTP API, allowing Home Assistant to ask you questions and receive voice responses.

## 📋 Requirements

- **Windows 10/11** (64-bit)
- **Home Assistant** server (2024.6+ recommended for native voice satellites)
- **Microphone and Speakers** connected to your PC
- **Long-lived access token** from Home Assistant (optional — only needed for media player volume control)

## 🛠️ Installation

### Option 1: Windows Installer (Recommended)
1. Download `WinVE-Setup.exe` from the latest release.
2. Run the installer and follow the wizard.
3. Configure your device name (default `WinVE`) and optional Home Assistant credentials for media player volume control.
4. Launch the application.
5. In Home Assistant, go to **Settings → Devices & Services**. WinVE will be automatically discovered via mDNS. Click **Configure** to add it.

### Option 2: From Source (For developers)

1. Clone the repository:
   ```bash
   git clone https://github.com/SmolinskiP/WinVE.git
   cd WinVE
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   pip install flet>=0.21.0
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## ⚙️ Home Assistant Integration

Once WinVE is running:
1. Go to Home Assistant **Settings → Devices & Services**.
2. If not auto-discovered, click **Add Integration**, search for **ESPHome**, and enter your PC's IP address and port `6053`.
3. You can configure which voice assistant pipeline WinVE uses directly from the ESPHome integration page in Home Assistant.

### Optional: Media Player Volume Control
If you want WinVE to duck your TV or speaker volume while you are speaking to it:
1. Open WinVE Settings from the system tray.
2. Under the **Media Players** tab, enter your Home Assistant Server Address and a Long-Lived Access Token (generate this in HA under Profile → Security → Long-Lived Access Tokens).
3. Specify the entity IDs of the media players you want to manage (comma-separated, e.g., `media_player.living_room_tv, media_player.kitchen_speaker`).

## 🔄 Interactive Prompts API

WinVE runs a local HTTP server (default port `8766`) that accepts incoming prompt requests, allowing Home Assistant to initiate conversations (e.g., "The garage door is open. Should I close it?").

**Endpoint**: `POST http://<YOUR_PC_IP>:8766/prompt`

**Request format**:
```json
{
  "message": "Would you like me to close the garage door?",
  "context": "Ask the user if they want to close the garage door.",
  "timeout": 15,
  "wait_for_response": true
}
```

## 📄 License

MIT License. Feel free to use, modify, and distribute this software.

---

<sub>WinVE is forked from [GLaSSIST 3.0](https://github.com/SmolinskiP/GLaSSIST) by SmolinskiP.</sub>
