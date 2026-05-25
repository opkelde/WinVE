"""
Wake Word Accuracy and False-Alarm Logger for WinVE.
Records wake word trigger events, saves audio buffers around detections,
and compiles performance metrics to calibrate ONNX detection thresholds.
"""
import os
import wave
import time
import json
import collections

class WakeWordAccuracyLogger:
    """Manages audio buffer caching and metadata logging for wake word performance analysis."""
    
    def __init__(self, sample_rate=16000, buffer_duration_sec=3.0, output_dir=None):
        self.sample_rate = sample_rate
        self.bytes_per_sample = 2  # 16-bit audio
        self.channels = 1
        
        # Audio buffer sizes
        self.buffer_size_bytes = int(sample_rate * buffer_duration_sec * self.bytes_per_sample)
        # Ring buffer to keep last 3 seconds of raw audio frames
        self.audio_ring_buffer = collections.deque(maxlen=self.buffer_size_bytes // 2) # maxlen in 16-bit elements
        
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "..", "wake_word_logs")
        self.log_file = os.path.join(self.output_dir, "accuracy_log.json")
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def write_audio_chunk(self, raw_data):
        """Pushes raw PCM audio chunk into the sliding ring buffer."""
        # Convert bytes to short elements
        import numpy as np
        samples = np.frombuffer(raw_data, dtype=np.int16)
        self.audio_ring_buffer.extend(samples)

    def log_trigger_event(self, model_name, confidence, threshold_used):
        """Called when a wake word event triggers. Saves the buffer and records entry."""
        timestamp = time.time()
        event_id = f"ww_{int(timestamp)}_{int((timestamp % 1) * 1000)}"
        audio_filename = f"{event_id}_{model_name}.wav"
        audio_path = os.path.join(self.output_dir, audio_filename)
        
        # Save buffered audio to a WAV file
        self._save_buffer_to_wav(audio_path)
        
        # Create metadata entry
        entry = {
            "event_id": event_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "unix_time": timestamp,
            "model_name": model_name,
            "confidence": float(confidence),
            "threshold_used": float(threshold_used),
            "audio_file": audio_filename,
            "user_validation": "UNVERIFIED" # Can be updated to TRUE_POSITIVE or FALSE_POSITIVE
        }
        
        self._append_to_json_log(entry)
        print(f"🎯 Accuracy Logger: Saved trigger audio to {audio_filename} (Confidence: {confidence:.3f})")
        return event_id

    def validate_event(self, event_id, is_true_positive):
        """Updates log validation status based on user action."""
        if not os.path.exists(self.log_file):
            return False
            
        try:
            with open(self.log_file, "r") as f:
                data = json.load(f)
        except Exception:
            data = []
            
        updated = False
        for entry in data:
            if entry.get("event_id") == event_id:
                entry["user_validation"] = "TRUE_POSITIVE" if is_true_positive else "FALSE_POSITIVE"
                updated = True
                break
                
        if updated:
            with open(self.log_file, "w") as f:
                json.dump(data, f, indent=4)
            print(f"✅ Event {event_id} marked as {'TRUE_POSITIVE' if is_true_positive else 'FALSE_POSITIVE'}")
            return True
        return False

    def _save_buffer_to_wav(self, file_path):
        """Converts ring buffer contents to a WAV file."""
        import numpy as np
        samples = np.array(self.audio_ring_buffer, dtype=np.int16)
        
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.bytes_per_sample)
                wf.setframerate(self.sample_rate)
                wf.writeframes(samples.tobytes())
        except Exception as e:
            print(f"Error saving wave file: {e}")

    def _append_to_json_log(self, entry):
        """Safely appends a JSON entry to the log file list."""
        data = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f:
                    data = json.load(f)
            except Exception:
                data = []
                
        data.append(entry)
        
        try:
            with open(self.log_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error writing to accuracy log: {e}")

    def get_summary_stats(self):
        """Calculates current false alarm rate vs true positive rate."""
        if not os.path.exists(self.log_file):
            return {"total": 0, "tp": 0, "fp": 0, "accuracy": 1.0}
            
        try:
            with open(self.log_file, "r") as f:
                data = json.load(f)
        except Exception:
            return {"total": 0, "tp": 0, "fp": 0, "accuracy": 1.0}
            
        tp = sum(1 for e in data if e.get("user_validation") == "TRUE_POSITIVE")
        fp = sum(1 for e in data if e.get("user_validation") == "FALSE_POSITIVE")
        unverified = sum(1 for e in data if e.get("user_validation") == "UNVERIFIED")
        
        total_verified = tp + fp
        accuracy = tp / total_verified if total_verified > 0 else 1.0
        
        return {
            "total_triggers": len(data),
            "true_positives": tp,
            "false_positives": fp,
            "unverified": unverified,
            "verified_accuracy_rate": accuracy
        }

if __name__ == "__main__":
    # Test harness
    import numpy as np
    
    logger = WakeWordAccuracyLogger(output_dir="ww_logs_demo")
    
    # Simulate a stream of ambient audio (white noise)
    print("Simulating audio stream...")
    for _ in range(60): # ~3 seconds of data chunks
        fake_chunk = np.random.randint(-100, 100, 800, dtype=np.int16).tobytes() # 800 samples chunk (50ms)
        logger.write_audio_chunk(fake_chunk)
        
    # Simulate wake word trigger
    print("\n🎯 Simulating wake word trigger event...")
    event_id = logger.log_trigger_event("jarvis", 0.76, 0.50)
    
    # Simulate user verifying it was a false alarm
    print("\n✍️ Simulating user marking event as FALSE POSITIVE...")
    logger.validate_event(event_id, is_true_positive=False)
    
    # Show stats
    print("\nSummary Statistics:")
    print(json.dumps(logger.get_summary_stats(), indent=2))
    
    # Cleanup demonstration folder
    try:
        import shutil
        shutil.rmtree("ww_logs_demo")
        print("\nCleanup demo directory.")
    except Exception:
        pass
