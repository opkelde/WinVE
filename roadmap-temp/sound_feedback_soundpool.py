"""
Prototype Implementation: SoundPool Low-Latency Feedback
Stored in roadmap-temp/ for reference and future integration.
"""
import sounddevice as sd
import soundfile as sf
import os
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_soundpool")

class AudioFeedbackSoundPool:
    """Pre-loads activation, deactivation, and alert WAV files in-memory to eliminate disk load latency during voice trigger events."""
    
    def __init__(self, sound_dir: str = None):
        if sound_dir is None:
            self.sound_dir = os.path.join(os.path.dirname(__file__), "..", "sound")
        else:
            self.sound_dir = sound_dir
            
        self.pool = {} # Dict caching raw audio array: {filename: (numpy_array, sample_rate)}
        self.load_lock = threading.Lock()
        
        # Files to pre-load
        self.preload_files = ["activation.wav", "deactivation.wav", "timer_finished.wav"]
        self.preload_sounds()

    def preload_sounds(self):
        """Read files into memory buffer."""
        with self.load_lock:
            for filename in self.preload_files:
                path = os.path.join(self.sound_dir, filename)
                if os.path.exists(path):
                    try:
                        logger.info(f"Pre-loading sound file to memory pool: {filename}")
                        data, samplerate = sf.read(path, dtype='float32')
                        self.pool[filename] = (data, samplerate)
                    except Exception as e:
                        logger.error(f"Failed to pre-load sound file {filename}: {e}")
                else:
                    logger.warning(f"Pre-load sound file not found: {path}")

    def play(self, filename: str, volume: float = 1.0):
        """Play a pre-loaded sound file instantly from memory buffer."""
        # Check pool
        if filename not in self.pool:
            logger.warning(f"Sound '{filename}' not in pool, loading dynamically...")
            # Fallback to load on the fly
            path = os.path.join(self.sound_dir, filename)
            if os.path.exists(path):
                try:
                    data, samplerate = sf.read(path, dtype='float32')
                    # Cache it
                    with self.load_lock:
                        self.pool[filename] = (data, samplerate)
                except Exception as e:
                    logger.error(f"Failed to load dynamic sound: {e}")
                    return
            else:
                logger.error(f"Sound file not found: {filename}")
                return
                
        # Play cached data
        try:
            data, samplerate = self.pool[filename]
            # Apply volume gain
            adjusted_data = data * volume
            
            logger.info(f"Playing from memory soundpool: {filename} (Vol: {volume:.2f})")
            # Start non-blocking playback
            sd.play(adjusted_data, samplerate)
        except Exception as e:
            logger.error(f"Failed to play soundpool buffer: {e}")

    def stop(self):
        """Immediately stops all active soundpool playbacks."""
        try:
            sd.stop()
            logger.info("SoundPool playbacks stopped.")
        except Exception as e:
            logger.error(f"Error stopping sound playback: {e}")
