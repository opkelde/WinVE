# Wake Word Model Customization for openWakeWord

## Overview
WinVE relies on `openWakeWord` for wake word detection. While default models like "Alexa" or "Hey Jarvis" are included, users often want custom wake words. Since openWakeWord uses deep learning models (specifically based on the ResNet or MobileNet architectures), custom models require training. This document outlines the pipeline for generating and optimizing custom `.onnx` models.

## Training Pipeline Overview
Training a high-quality wake word model from scratch normally requires thousands of recorded audio clips of the wake word spoken by diverse voices. openWakeWord solves this using **Synthetic Speech Generation** to automate training data collection.

### 1. Synthetic Data Generation
- **Tooling**: Uses Text-to-Speech (TTS) models (such as Piper, Coqui TTS, or Microsoft Edge TTS) to synthesize the wake word.
- **Process**:
  - Generate 10,000+ audio clips of the target wake word.
  - Vary the speed, pitch, tone, accent, and pronunciation of the synthesis.
  - Synthesize a large set of "negative" words (phonetically similar words and random words) to prevent false triggers.

### 2. Audio Augmentation
To make the model robust in real-world environments, the synthesized audio is mixed with background noise:
- Add ambient noise (fan hums, street sounds, keyboard clicks).
- Add indoor reverberation models (simulating large rooms or echoing offices).
- Randomly shift audio pitch and volume.

### 3. Model Training
- **Framework**: PyTorch.
- **Architecture**: A compact CNN model trained on the generated mel-spectrogram database.
- **Output**: A PyTorch weights file (`.pth`).

## Exporting and Quantizing to ONNX
ONNX (Open Neural Network Exchange) is the target format for Windows deployment because it runs efficiently on the CPU without PyTorch dependencies.

### 1. PyTorch to ONNX Export
```python
import torch

# Load the trained PyTorch model
model = CustomWakeWordModel()
model.load_state_dict(torch.load("model.pth"))
model.eval()

# Dummy input representing standard spectrogram features
dummy_input = torch.randn(1, 16, 96) # batch, frames, features

# Export
torch.onnx.export(
    model, 
    dummy_input, 
    "custom_wakeword.onnx",
    input_names=["input"],
    output_names=["output"],
    dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}
)
```

### 2. ONNX Quantization (Optimization)
To minimize resource usage, models are quantized from 32-bit floating-point parameters (FP32) to 8-bit integers (INT8). This reduces model size by 75% and speeds up inference with negligible loss in accuracy.

Using the `onnxruntime.quantization` module:
```python
from onnxruntime.quantization import quantize_dynamic, QuantType

quantize_dynamic(
    model_input="custom_wakeword.onnx",
    model_output="custom_wakeword_quant.onnx",
    weight_type=QuantType.QUInt8
)
```
The resulting file is renamed to `<wakeword_name>.onnx` and placed into WinVE's `models/` directory.

## Deployment Checklist
For WinVE to recognize the new model:
1. Ensure the file name matches the desired wake word (e.g. `computer_v2.onnx`).
2. Verify the model file is located in the folder returned by `WakeWordDetector.models_dir`.
3. Update the `HA_WAKE_WORD_MODELS` environment variable/settings value to include the new model name (without the `.onnx` extension).
