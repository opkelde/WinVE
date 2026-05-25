"""
Prototype Implementation: Universal Windows Session Ducking
Stored in roadmap-temp/ for reference and future integration.
"""
import ctypes
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_audio_ducking")

class WindowsAudioDuckingManager:
    """Manages system-wide audio ducking (reducing background volume) using WASAPI via pycaw or ctypes."""
    
    def __init__(self):
        self.is_ducked = False
        self.duck_amount = 0.20 # Duck background audio to 20% of original volume
        self.original_volumes = {} # Cache original volumes: {SessionIdentifier: volume_level}

    def duck_all_sessions(self):
        """Reduces the volume of all active audio sessions in Windows."""
        if self.is_ducked:
            return
            
        logger.info("Initiating system-wide background audio ducking...")
        
        # We run this in a background thread to prevent blocking the main audio recording loop
        threading.Thread(target=self._run_ducking, daemon=True).start()

    def _run_ducking(self):
        try:
            from pycaw.pycaw import AudioUtilities
            
            self.original_volumes.clear()
            sessions = AudioUtilities.GetAllSessions()
            
            for session in sessions:
                # Exclude the voice assistant process itself (WinVE) to avoid ducking its own TTS feedback
                if session.Process and session.Process.name().lower() in ("winve.exe", "python.exe"):
                    continue
                    
                volume_control = session.SimpleAudioVolume
                current_vol = volume_control.GetMasterVolume()
                
                # Cache the original volume to restore it later
                session_id = session.Identifier
                self.original_volumes[session_id] = current_vol
                
                # Apply ducking
                ducked_vol = current_vol * self.duck_amount
                volume_control.SetMasterVolume(ducked_vol, None)
                logger.debug(f"Ducked session '{session.Process.name() if session.Process else 'System'}' from {current_vol:.2f} -> {ducked_vol:.2f}")
                
            self.is_ducked = True
            logger.info("Audio sessions ducked successfully.")
            
        except ImportError:
            logger.warning("pycaw is not installed. System-wide ducking bypassed.")
            # Fallback: attempt to execute simple Windows media key mute/lower volume command
            self._fallback_ducking()
        except Exception as e:
            logger.error(f"Error during audio session ducking: {e}")

    def restore_all_sessions(self):
        """Restores original volume for all sessions."""
        if not self.is_ducked:
            return
            
        logger.info("Restoring background audio session volumes...")
        threading.Thread(target=self._run_restore, daemon=True).start()

    def _run_restore(self):
        try:
            from pycaw.pycaw import AudioUtilities
            
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                session_id = session.Identifier
                if session_id in self.original_volumes:
                    volume_control = session.SimpleAudioVolume
                    restored_vol = self.original_volumes[session_id]
                    volume_control.SetMasterVolume(restored_vol, None)
                    logger.debug(f"Restored session '{session.Process.name() if session.Process else 'System'}' to {restored_vol:.2f}")
                    
            self.is_ducked = False
            self.original_volumes.clear()
            logger.info("Audio sessions restored successfully.")
            
        except Exception as e:
            logger.error(f"Error restoring audio session volumes: {e}")

    def _fallback_ducking(self):
        """Fallback: uses simple Windows Wscript Shell mute commands."""
        # Simple volume lower script
        cmd = "$wsh = New-Object -ComObject Wscript.Shell; for($i=0; $i -lt 5; $i++) { $wsh.SendKeys([char]174) }" # Media Volume Down
        import subprocess
        subprocess.run(["powershell", "-Command", cmd], capture_output=True)
