"""
Voice Biometrics & Speaker Verification for WinVE.
Extracts speech feature templates (MFCC-like mel frequency profiles) from authorized users
and performs cosine similarity verification to restrict sensitive system commands
from running on unauthorized voices.
"""
import os
import json
import numpy as np

class VoiceBiometricsManager:
    """Manages enrollment of authorized speakers and performs verification on incoming audio."""
    
    def __init__(self, database_path=None):
        self.database_path = database_path or os.path.join(os.path.dirname(__file__), "..", "speaker_biometrics.json")
        self.speaker_profiles = {}
        self.load_profiles()

    def load_profiles(self):
        """Loads enrolled speaker voice profiles."""
        if os.path.exists(self.database_path):
            try:
                with open(self.database_path, "r", encoding="utf-8") as f:
                    # Convert lists back to numpy arrays during loading
                    data = json.load(f)
                    self.speaker_profiles = {
                        name: np.array(profile) for name, profile in data.items()
                    }
            except Exception as e:
                print(f"Error loading biometrics database: {e}")
                self.speaker_profiles = {}

    def save_profiles(self):
        """Saves speaker profiles back to the database file."""
        try:
            # Convert numpy arrays to lists for JSON serialization
            serializable = {
                name: profile.tolist() for name, profile in self.speaker_profiles.items()
            }
            with open(self.database_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=4)
        except Exception as e:
            print(f"Error saving biometrics database: {e}")

    def extract_voice_signature(self, audio_data, sample_rate=16000):
        """
        Extracts a feature vector representing the speaker's vocal characteristics.
        Computes a simplified Mel-Filterbank energy profile (MFCC-like representation).
        """
        # Convert raw byte/int16 data to float32
        if isinstance(audio_data, bytes):
            audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        else:
            audio = np.asarray(audio_data, dtype=np.float32)
            
        # 1. Apply pre-emphasis filter to boost high frequencies
        audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])
        
        # 2. Frame the signal (e.g. 512-sample frames with 256 overlap)
        frame_len = 512
        hop_len = 256
        frames = []
        for i in range(0, len(audio) - frame_len, hop_len):
            # Windowing (Hamming Window)
            window = np.hamming(frame_len)
            frames.append(audio[i:i+frame_len] * window)
            
        if not frames:
            return np.zeros(20) # Fallback vector
            
        # 3. Compute Power Spectrum using FFT
        power_spectra = []
        for frame in frames:
            fft_complex = np.fft.rfft(frame, n=512)
            power_spectrum = (1.0 / 512) * (np.abs(fft_complex) ** 2)
            power_spectra.append(power_spectrum)
            
        # 4. Construct Mel-Filterbank (20 filters from 100Hz to 8000Hz)
        # For simplicity in a prototype, compile a lightweight 20-band energy accumulator
        mel_energies = []
        for spec in power_spectra:
            # Group FFT bins into 20 bands logarithmically spaced
            bands = np.array_split(spec, 20)
            mel_energies.append([np.sum(b) for b in bands])
            
        # 5. Average across time to create a stationary speaker signature/template
        avg_mel_profile = np.mean(mel_energies, axis=0)
        
        # 6. Apply Log to mimic human hearing and normalize
        log_profile = np.log10(np.clip(avg_mel_profile, 1e-5, None))
        norm_profile = log_profile - np.mean(log_profile)
        magnitude = np.linalg.norm(norm_profile)
        
        if magnitude > 0:
            norm_profile = norm_profile / magnitude
            
        return norm_profile

    def enroll_speaker(self, name, enrollment_audio_clips):
        """Enrolls a speaker by averaging signatures from multiple voice clips."""
        signatures = []
        for clip in enrollment_audio_clips:
            sig = self.extract_voice_signature(clip)
            signatures.append(sig)
            
        # Average enrolled signature
        mean_signature = np.mean(signatures, axis=0)
        # Normalize
        norm_sig = mean_signature / np.linalg.norm(mean_signature)
        
        self.speaker_profiles[name] = norm_sig
        self.save_profiles()
        print(f"👤 Biometrics: Speaker '{name}' enrolled successfully.")
        return True

    def verify_speaker(self, incoming_audio, threshold=0.75):
        """
        Compares incoming audio against enrolled profiles.
        Returns the matched speaker name if similarity exceeds the threshold.
        """
        if not self.speaker_profiles:
            return None, 0.0, "No enrolled profiles."
            
        incoming_sig = self.extract_voice_signature(incoming_audio)
        
        best_match = None
        highest_similarity = -1.0
        
        for name, profile in self.speaker_profiles.items():
            # Cosine similarity (profiles are normalized vectors, so dot product works directly)
            similarity = np.dot(profile, incoming_sig)
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = name
                
        if highest_similarity >= threshold:
            return best_match, highest_similarity, "VERIFIED"
        
        return None, highest_similarity, "UNAUTHORIZED"

if __name__ == "__main__":
    # Test execution harness simulating enrollments and tests
    biometrics = VoiceBiometricsManager(database_path="biometrics_demo.json")
    
    # Generate mock speaker audios (different random seeds simulate different vocal frequencies)
    np.random.seed(42)
    user_alice_clip1 = np.random.normal(0.0, 1.0, 16000 * 2) # Alice speaking (2s)
    user_alice_clip2 = np.random.normal(0.0, 1.0, 16000 * 2)
    user_alice_test = np.random.normal(0.0, 1.0, 16000 * 2) # Alice test clip
    
    np.random.seed(99)
    intruder_clip = np.random.normal(0.0, 1.5, 16000 * 2)  # Different pitch profile
    
    # Enroll Alice
    biometrics.enroll_speaker("Alice", [user_alice_clip1, user_alice_clip2])
    
    # Verify Alice test
    user, score, status = biometrics.verify_speaker(user_alice_test, threshold=0.70)
    print(f"\nAlice test verification: matched user='{user}' (score: {score:.3f}, status: {status})")
    
    # Verify Intruder
    user, score, status = biometrics.verify_speaker(intruder_clip, threshold=0.70)
    print(f"Intruder verification: matched user='{user}' (score: {score:.3f}, status: {status})")
    
    # Cleanup demo database
    if os.path.exists("biometrics_demo.json"):
        os.remove("biometrics_demo.json")
