"""
Prototype Implementation: Local Offline TTS Fallback
Stored in roadmap-temp/ for reference and future integration.
"""
import os
import subprocess
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_offline_tts")

class OfflineTTSFallback:
    """Manages text-to-speech output when connection to Home Assistant pipeline is offline."""
    
    def __init__(self, voice_id: int = 0):
        self.voice_id = voice_id # 0 for male, 1 for female (standard SAPI5 voices)
        self.piper_path = os.path.join(os.path.dirname(__file__), "bin", "piper.exe")
        self.piper_model = os.path.join(os.path.dirname(__file__), "bin", "en_US-lessac-medium.onnx")

    def speak(self, text: str):
        """Dispatches speech request. Tries Piper first, then falls back to pyttsx3 SAPI5."""
        logger.info(f"Offline TTS request: '{text}'")
        
        # Check if local Piper binary exists
        if os.path.exists(self.piper_path) and os.path.exists(self.piper_model):
            threading.Thread(target=self._speak_piper, args=(text,), daemon=True).start()
        else:
            threading.Thread(target=self._speak_pyttsx3, args=(text,), daemon=True).start()

    def _speak_pyttsx3(self, text: str):
        """Uses Windows built-in SAPI5 TTS engine via pyttsx3 library."""
        try:
            import pyttsx3
            
            # Initialize local SAPI5 engine
            engine = pyttsx3.init(driverName="sapi5")
            
            # Configure voice
            voices = engine.getProperty("voices")
            if voices:
                # Select requested voice or default
                target_idx = min(self.voice_id, len(voices) - 1)
                engine.setProperty("voice", voices[target_idx].id)
                
            engine.setProperty("rate", 180) # Speaking speed
            
            logger.info("Speaking offline text via SAPI5 SAPI5 engine...")
            engine.say(text)
            engine.runAndWait()
            logger.info("Speech finished.")
            
        except ImportError:
            logger.warning("pyttsx3 is not installed. Attempting direct powershell speech output...")
            self._speak_powershell(text)
        except Exception as e:
            logger.error(f"SAPI5 offline speech failed: {e}")

    def _speak_piper(self, text: str):
        """Uses compiled Piper binary (local Neural voice) for high-quality offline TTS."""
        try:
            import sounddevice as sd
            import soundfile as sf
            
            output_wav = os.path.join(os.path.dirname(__file__), "temp_tts.wav")
            
            # Run Piper subprocess to generate the WAV file
            # piper.exe --model model.onnx --output_file out.wav
            cmd = [
                self.piper_path,
                "--model", self.piper_model,
                "--output_file", output_wav
            ]
            
            logger.info("Synthesizing speech via local Piper TTS ONNX model...")
            # Send text into stdin
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate(input=text.encode('utf-8'))
            
            if os.path.exists(output_wav):
                # Play output file using sounddevice/soundfile
                data, fs = sf.read(output_wav)
                sd.play(data, fs)
                sd.wait()
                # Cleanup temporary file
                os.remove(output_wav)
                logger.info("Piper speech playback completed.")
            else:
                logger.error("Piper output file was not generated.")
                
        except Exception as e:
            logger.error(f"Piper offline speech failed: {e}. Falling back to SAPI5.")
            self._speak_pyttsx3(text)

    def _speak_powershell(self, text: str):
        """Low-level powershell command fallback utilizing system SpeechSynthesizer."""
        try:
            logger.info("Speaking offline text via PowerShell SpeechSynthesizer...")
            powershell_cmd = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$synth.Speak('{text}')"
            )
            subprocess.run(["powershell", "-Command", powershell_cmd], capture_output=True)
            logger.info("PowerShell speech finished.")
        except Exception as e:
            logger.error(f"PowerShell speech failed: {e}")
