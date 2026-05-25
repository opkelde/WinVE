"""
Voice Profile Analyzer for WinVE.
Analyzes user pitch, frequency components, and ambient noise floor
to calibrate Voice Activity Detection (VAD) thresholds and filters.
"""
import pyaudio
import numpy as np
import time

class VoiceProfileAnalyzer:
    """Analyzes microphone audio streams to calibrate speech activity and threshold parameters."""
    
    def __init__(self, rate=16000, chunk=1024):
        self.rate = rate
        self.chunk = chunk
        self.p = pyaudio.PyAudio()
        
    def measure_noise_floor(self, duration=3.0):
        """Records ambient noise to estimate silence floor."""
        print(f"🤫 Calibrating noise floor... Keep silent for {duration} seconds.")
        stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        energies = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            data = stream.read(self.chunk, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            # Root Mean Square energy
            rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
            energies.append(rms)
            
        stream.stop_stream()
        stream.close()
        
        avg_noise = np.mean(energies)
        max_noise = np.max(energies)
        print(f"✅ Noise floor analysis: Average RMS = {avg_noise:.2f}, Peak RMS = {max_noise:.2f}")
        return avg_noise, max_noise

    def analyze_voice_pitch(self, duration=5.0):
        """Measures fundamental frequency (F0) of the user's voice during speech using Autocorrelation."""
        print(f"🗣️ Please speak or hum naturally for {duration} seconds...")
        stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        pitches = []
        energies = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            data = stream.read(self.chunk, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            
            # 1. Measure energy
            rms = np.sqrt(np.mean(audio_data**2))
            energies.append(rms)
            
            # Only analyze pitch if voice energy is sufficient
            if rms > 150: 
                # 2. Autocorrelation method for pitch detection
                # Normalize audio
                corr = np.correlate(audio_data, audio_data, mode='full')
                corr = corr[len(corr)//2:]
                
                # Find peaks in the typical human speech pitch range: 80Hz to 400Hz
                # At 16000Hz sampling rate, periods correspond to samples indices:
                # 16000 / 400 = 40 samples minimum lag
                # 16000 / 80 = 200 samples maximum lag
                min_lag = int(self.rate / 400)
                max_lag = int(self.rate / 80)
                
                # Look for peak in this interval
                if len(corr) > max_lag:
                    lag_range = corr[min_lag:max_lag]
                    if len(lag_range) > 0:
                        peak_lag = np.argmax(lag_range) + min_lag
                        pitch = self.rate / peak_lag
                        pitches.append(pitch)
                        
        stream.stop_stream()
        stream.close()
        
        if not pitches:
            print("⚠️ No sustained voice audio detected. Calibration inconclusive.")
            return None
            
        avg_pitch = np.mean(pitches)
        median_pitch = np.median(pitches)
        min_pitch = np.min(pitches)
        max_pitch = np.max(pitches)
        
        print(f"✅ Voice Pitch analysis completed:")
        print(f"   Median Pitch (F0): {median_pitch:.1f} Hz (Range: {min_pitch:.1f} - {max_pitch:.1f} Hz)")
        
        # Categorize voice
        voice_type = "Low/Baritone"
        if median_pitch > 165:
            voice_type = "High/Treble"
        elif median_pitch > 120:
            voice_type = "Tenor/Alto"
            
        print(f"   Estimated Voice Type: {voice_type}")
        return {
            "median_pitch": median_pitch,
            "voice_type": voice_type,
            "mean_energy": np.mean(energies)
        }

    def run_calibration(self):
        """Runs complete calibration and displays recommended settings."""
        print("=== WinVE Voice & Noise Calibration Tool ===")
        noise_avg, noise_max = self.measure_noise_floor()
        print("\n-------------------------------------------")
        voice_data = self.analyze_voice_pitch()
        
        if voice_data:
            # Calibrate settings
            # VAD threshold should be higher than ambient max, but lower than speaking average
            recommended_vad = min(0.9, max(0.15, (noise_max * 1.5) / voice_data["mean_energy"]))
            print("\n=== Recommended WinVE Configuration ===")
            print(f"• HA_WAKE_WORD_VAD_THRESHOLD: {recommended_vad:.2f}")
            print(f"• Voice Bandpass Filter Limits: {max(60, int(voice_data['median_pitch'] * 0.6))} Hz to {min(8000, int(voice_data['median_pitch'] * 3.5))} Hz")
            print("=======================================")
        else:
            print("\n❌ Calibration incomplete. Please try again in a quieter room.")
            
        self.p.terminate()

if __name__ == "__main__":
    analyzer = VoiceProfileAnalyzer()
    analyzer.run_calibration()
