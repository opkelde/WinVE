"""
Prototype Implementation: Keyboard Push-to-Talk (PTT) Mode
Stored in roadmap-temp/ for reference and future integration.
"""
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_ptt")

class PushToTalkManager:
    """Manages global keyboard hold-to-talk (Push-to-Talk) functionality for voice triggering."""
    
    def __init__(self, main_app=None):
        self.main_app = main_app
        self.ptt_key = "space" # Hold space bar (or other modifier) to speak
        self.is_holding = False
        self.is_listening = False
        
        # Debounce to prevent rapid triggers
        self.last_key_event_time = 0
        self.debounce_seconds = 0.2

    def start_listener(self):
        """Register the global key hold and release hooks."""
        logger.info(f"Initializing Push-to-Talk. Target PTT Key: '{self.ptt_key}'")
        
        # In actual implementation:
        # import keyboard
        # keyboard.on_press_key(self.ptt_key, self._on_key_down)
        # keyboard.on_release_key(self.ptt_key, self._on_key_up)

    def _on_key_down(self, event):
        """Triggered when target key is pressed down."""
        now = time.time()
        if now - self.last_key_event_time < self.debounce_seconds:
            return
            
        if not self.is_holding:
            self.is_holding = True
            self.last_key_event_time = now
            logger.info("PTT Key Down: Listening started.")
            
            # Stop wake word engine and immediately begin recording audio stream
            if self.main_app:
                # Trigger pipeline session start
                threading.Thread(target=self.main_app.trigger_voice_command, args=(True,), daemon=True).start()

    def _on_key_up(self, event):
        """Triggered when target key is released."""
        if self.is_holding:
            self.is_holding = False
            self.last_key_event_time = time.time()
            logger.info("PTT Key Up: Listening stopped. Processing...")
            
            # Signal the audio recorder to wrap up the streaming package and process pipeline
            if self.main_app and hasattr(self.main_app, "audio_manager"):
                self.main_app.audio_manager.stop_recording()

    def update_keybind(self, new_key: str):
        """Safely hot-swaps PTT shortcut key."""
        logger.info(f"Updating PTT Key: {self.ptt_key} -> {new_key}")
        # Unregister old key, register new key
        self.ptt_key = new_key
