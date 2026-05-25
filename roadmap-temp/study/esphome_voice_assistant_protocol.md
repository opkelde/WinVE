# ESPHome Voice Assistant Protocol

## Overview
WinVE can operate as an ESPHome-compatible voice satellite. This allows Home Assistant to recognize it as a local voice assistant node and stream audio using Home Assistant's native audio pipeline (Wyoming / pipeline architecture). The protocol consists of a TCP API handshake followed by a raw UDP audio stream.

## Protocol Handshake (TCP)
ESPHome nodes communicate with Home Assistant's API port (typically `6053`) using the ESPHome Native API Protocol, which uses Protocol Buffers (protobuf) for structured messaging.

1. **Connection**: The satellite client connects to Home Assistant's API socket.
2. **Hello Request / Response**: Negotiates connection keys, encryption (if configured), and protocol version.
3. **Voice Assistant Subscription**:
   - The satellite announces it supports the `VOICE_ASSISTANT` feature flag.
   - It sends a subscription command to start receiving audio pipeline events.

## Audio Streaming (UDP)
Once the handshake completes and a session is active, audio transmission switches to UDP to ensure real-time, low-latency delivery.

### 1. Satellite -> Home Assistant (Microphone Stream)
- When the wake word is detected locally (or when manual recording is triggered), the satellite opens a UDP socket to Home Assistant.
- **Audio Payload Format**:
  - Codec: **PCM 16-bit Signed integer**, Little-Endian.
  - Channels: 1 (Mono).
  - Sample Rate: **16,000 Hz**.
  - Frame Duration: Typically 20ms or 32ms per packet (e.g. 640 or 1024 bytes per UDP packet).
- The packet contains a small header containing a session sequence number followed by the raw PCM frames.

### 2. Home Assistant -> Satellite (TTS Output Stream)
- After processing the query, Home Assistant generates a Text-to-Speech (TTS) response.
- The Wyoming voice pipeline sends this audio back to the satellite over UDP.
- **TTS Payload Format**:
  - Codec: **PCM 16-bit** (or optionally compressed Opus in modern setups).
  - Sample Rate: Typically 16kHz or 22.05kHz.
- The satellite receives these packets and plays them back through the system speakers.

## Pipeline Event Messages
During a voice session, Home Assistant sends status event messages back to the TCP socket to update the satellite's state. Key events include:
- **`VOICE_ASSISTANT_LISTEN`**: Home Assistant is listening (VAD active).
- **`VOICE_ASSISTANT_STT_START`**: Speech-to-text processing has started.
- **`VOICE_ASSISTANT_STT_END`**: Speech-to-text finished. The transcript text is attached.
- **`VOICE_ASSISTANT_INTENT_START`**: Intent recognition running (interpreting transcript).
- **`VOICE_ASSISTANT_INTENT_END`**: Intent resolved (e.g., light toggled).
- **`VOICE_ASSISTANT_TTS_START`**: TTS audio generation started.
- **`VOICE_ASSISTANT_TTS_END`**: TTS audio generation finished.
- **`VOICE_ASSISTANT_ERROR`**: Handlers failed or connection timed out.

## WinVE Implementation Details
In `satellite_protocol.py`, WinVE implements an ESPHome-compatible server. It listens on port `10446` (or similar configured port) and mimics an ESPHome device. When Home Assistant scans the network and connects to WinVE, the system responds with the expected API frames. This allows the WinVE endpoint to masquerade as an ESPHome voice satellite without requiring physical hardware modifications or compilation.
