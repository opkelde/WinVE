# Training Voice Models for Custom Spells

## Overview
Voice spells in WinVE (e.g., *"Lumos"*, *"Nox"*, *"Alohomora"*) are key phrases that bypass the primary wake word to execute actions immediately. Because they are always-on and run locally on Windows, they require dedicated, lightweight keyword spotting (KWS) models that do not block system resources. This document details the research, training, and deployment pipelines for custom spell voice models.

---

## Technical Approaches

### 1. Custom openWakeWord ONNX Models (Recommended)
- **Concept**: Training a custom classification model using openWakeWord's training repository.
- **Why it fits**: WinVE already uses the `openWakeWord` framework on ONNX Runtime. Loading additional `.onnx` models for spells (e.g., `lumos.onnx`) integrates natively with zero code modifications.
- **Training Pipeline**:
  1. Generate 10,000+ synthetic audio files of the word "Lumos" using different TTS engines (Piper, Edge-TTS).
  2. Synthesize 20,000+ negative samples (common words, room noises, phone rings).
  3. Train a lightweight fully-connected neural network on pre-extracted MobileNetV3 embeddings.
  4. Export to ONNX and apply 8-bit dynamic quantization.
- **Performance**: Extremely fast (~1-2% CPU overhead per model), fully local, and runs in parallel with the main wake word detector.

### 2. Local Whisper-Tiny Streaming (Speech-to-Text)
- **Concept**: Continuous audio buffering with local transcription via a quantized Whisper model (e.g. `faster-whisper` or `whisper.cpp` Python bindings).
- **Why it fits**: Highly accurate and can detect any custom spells dynamically typed by the user without requiring retraining.
- **How it works**:
  - A rolling 3-second audio buffer is fed into the Whisper-Tiny model whenever Voice Activity Detection (VAD) detects speech.
  - The resulting text transcript is checked against the user's custom spell keywords using regex.
- **Performance**: High accuracy, but higher CPU/VRAM usage (~10-25% CPU during transcription). Best suited for high-end PCs or when users change spells frequently.

### 3. PocketSphinx Keyphrase Spotting (Grammar-based KWS)
- **Concept**: CMU Sphinx provides a lightweight offline speech recognition library that supports keyphrase search mode.
- **Why it fits**: Lightweight, zero-dependency C-bindings (`pocketsphinx` Python package).
- **How it works**: You pass the model a list of keyphrases and a threshold (e.g., `lumos /1e-20/`), and the decoder only searches for those phonemes.
- **Performance**: Extremely low CPU overhead, but lower accuracy and high sensitivity to background noise compared to modern deep-learning approaches.

---

## openWakeWord Model Training Workflow (Step-by-Step)

To train a custom spell model (e.g., `lumos.onnx`) for WinVE:

### Step 1: Clone the openWakeWord Repository
Clone the official openWakeWord repository containing the training utilities:
```bash
git clone https://github.com/dscripka/openWakeWord.git
cd openWakeWord
pip install -r requirements.txt
```

### Step 2: Generate Synthetic Dataset
Create a dataset config file `lumos_config.yaml`:
```yaml
wakeword: lumos
generators:
  - edge_tts:
      voices: [en-US-AriaNeural, en-US-GuyNeural, en-GB-SoniaNeural]
  - piper:
      model: en_US-lessac-medium
```
Run the generation script to create positive samples of "Lumos" and mix them with background noise:
```bash
python scripts/generate_synthetic_data.py --config lumos_config.yaml --output_dir ./data
```

### Step 3: Train the Model
Train the classifier using the pre-computed embeddings:
```bash
python scripts/train_model.py --training_data ./data --model_name lumos --epochs 20
```
This produces a trained PyTorch weights file `lumos.pth`.

### Step 4: Export and Quantize to ONNX
Convert the PyTorch model to a quantized ONNX format:
```bash
python scripts/export_onnx.py --input_model lumos.pth --output_model models/lumos.onnx --quantize
```

### Step 5: Integrate into WinVE
Move `lumos.onnx` into the `models/` directory. Update the `HA_WAKE_WORD_MODELS` configuration variable:
```env
HA_WAKE_WORD_MODELS=computer_v2,lumos,nox
```

---

## Architectural Comparison for Spells

| Metric | openWakeWord ONNX | Whisper-Tiny Streaming | PocketSphinx |
| :--- | :--- | :--- | :--- |
| **Ideal for** | Specific fixed spells (e.g., "Lumos") | User-defined custom text phrases | Legacy/Low-spec hardware |
| **Accuracy** | High (Robust to noise) | Very High (Phoneme match) | Low-Medium (High false alarms) |
| **Memory** | ~20MB RAM | ~150MB - 250MB RAM | ~10MB RAM |
| **Latency** | < 100ms | 300ms - 800ms | < 150ms |
| **Training Needed**| Yes (Synthetic script) | No (Zero-shot transcript) | No (Phoneme dictionary) |
