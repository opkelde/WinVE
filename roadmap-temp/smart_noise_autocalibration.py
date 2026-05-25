"""
Prototype Implementation: Smart Noise Auto-Calibration
Stored in roadmap-temp/ for reference and future integration.
"""
import pyaudio
import numpy as np
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_noise_calibration")

class NoiseAutoCalibrator:
    """Performs an ambient noise scan to calibrate VAD sensitivity and silence thresholds."""
    
    def __init__(self, mic_index: int = -1):
        self.mic_index = mic_index
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.audio = pyaudio.PyAudio()

    def calibrate(self, duration_seconds: float = 3.0) -> dict:
        """Opens microphone stream, measures ambient noise levels, and calculates dynamic thresholds."""
        logger.info(f"Starting ambient noise auto-calibration on mic index {self.mic_index}...")
        
        try:
            device_index = None if self.mic_index == -1 else self.mic_index
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
        except Exception as e:
            logger.error(f"Failed to open audio stream for noise calibration: {e}")
            return {}

        energy_levels = []
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            try:
                # Read audio chunk
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                # Convert buffer to numpy array
                samples = np.frombuffer(data, dtype=np.int16)
                
                # Calculate Root Mean Square (RMS) energy
                rms = np.sqrt(np.mean(samples.astype(float)**2))
                energy_levels.append(rms)
            except Exception as e:
                logger.error(f"Error reading frame during calibration: {e}")
                
        stream.stop_stream()
        stream.close()

        if not energy_levels:
            logger.warning("No audio frames recorded, calibration aborted.")
            return {}

        # Calculate metrics
        avg_rms = np.mean(energy_levels)
        max_rms = np.max(energy_levels)
        std_rms = np.std(energy_levels)

        # Dynamic VAD & Silence calculations
        # VAD threshold needs to sit above the peak ambient noise floor.
        # Scale thresholds logarithmically or with a safety multiplier (e.g. mean + 3 * std).
        suggested_threshold = avg_rms + (3 * std_rms)
        
        # Normalize suggested_threshold relative to max possible int16 amplitude (32768)
        norm_avg = avg_rms / 32768.0
        norm_suggested = suggested_threshold / 32768.0

        # Adjust WebRTC VAD mode (0 is least aggressive, 3 is most aggressive)
        if norm_avg < 0.005:
            suggested_vad_mode = 1 # Quiet environment - low aggression
        elif norm_avg < 0.02:
            suggested_vad_mode = 2 # Normal office environment
        else:
            suggested_vad_mode = 3 # Loud / noisy environment - high VAD aggression

        results = {
            "ambient_average_rms": float(avg_rms),
            "ambient_peak_rms": float(max_rms),
            "suggested_silence_threshold": float(norm_suggested),
            "suggested_vad_mode": suggested_vad_mode
        }

        logger.info("Auto-calibration complete:")
        logger.info(f"  Ambient noise average: {norm_avg:.4f} RMS")
        logger.info(f"  Suggested silence limit: {norm_suggested:.4f}")
        logger.info(f"  Suggested VAD mode: {suggested_vad_mode}")

        return results

    def cleanup(self):
        self.audio.terminate()
