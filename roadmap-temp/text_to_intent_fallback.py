"""
Offline Text-To-Intent Parser and Action Router for WinVE.
Decodes text transcripts locally using pattern matching and keyword extraction
to execute local PC commands and media controls when Home Assistant is offline.
"""
import re
import os
import subprocess
import ctypes

class TextToIntentRouter:
    """Parses natural text strings to recognize intents and routes them to native Windows tasks."""
    
    def __init__(self):
        # Define rule-based intent patterns
        self.rules = [
            # Media control intents
            (r"\b(play|pause|resume)\b", self._handle_media_play_pause),
            (r"\b(next|skip)\s+song\b|\bnext\s+track\b", self._handle_media_next),
            (r"\b(previous|prev)\s+song\b|\bprev\s+track\b", self._handle_media_prev),
            
            # System audio intents
            (r"\b(mute|unmute)\b", self._handle_audio_mute),
            (r"\bvolume\s+up\b|\braise\s+volume\b", lambda: self._handle_audio_volume(change=10)),
            (r"\bvolume\s+down\b|\blower\s+volume\b", lambda: self._handle_audio_volume(change=-10)),
            (r"\bset\s+volume\s+to\s+(\d+)(?:\s*percent|\s*%)?\b", lambda m: self._handle_audio_volume(level=int(m.group(1)))),
            
            # Application launching intents
            (r"\b(open|launch|start)\s+(notepad|calculator|cmd|paint|browser|chrome|edge)\b", self._handle_launch_app),
            
            # Windows utilities
            (r"\b(take\s+a\s+)?screenshot\b", self._handle_screenshot),
            (r"\block\b.*\b(pc|computer|screen)\b", self._handle_lock_screen),
            (r"\bshutdown\b.*\b(pc|computer)\b", self._handle_shutdown),
        ]
        self.user32 = ctypes.windll.user32

    def process_text(self, text):
        """Analyzes text against regex rules and executes matching handlers."""
        cleaned_text = text.lower().strip()
        print(f"📝 Local Intent Router: Processing text: '{cleaned_text}'")
        
        for pattern, handler in self.rules:
            match = re.search(pattern, cleaned_text)
            if match:
                print(f"🎯 Matched intent pattern: '{pattern}'")
                # If the handler accepts match group arguments, pass it, else run normally
                try:
                    import inspect
                    sig = inspect.signature(handler)
                    if len(sig.parameters) > 0:
                        return True, handler(match)
                    else:
                        return True, handler()
                except Exception as e:
                    return False, f"Error running intent handler: {e}"
                    
        return False, "No local intent matched."

    # --- Handlers ---
    
    def _handle_media_play_pause(self):
        # 0xAD is VK_VOLUME_MUTE, 0xB3 is VK_MEDIA_PLAY_PAUSE
        self.user32.keybd_event(0xB3, 0, 0, 0)
        self.user32.keybd_event(0xB3, 0, 2, 0) # Key up
        return "Toggled play/pause"

    def _handle_media_next(self):
        # 0xB0 is VK_MEDIA_NEXT_TRACK
        self.user32.keybd_event(0xB0, 0, 0, 0)
        self.user32.keybd_event(0xB0, 0, 2, 0)
        return "Skipped to next track"

    def _handle_media_prev(self):
        # 0xB1 is VK_MEDIA_PREV_TRACK
        self.user32.keybd_event(0xB1, 0, 0, 0)
        self.user32.keybd_event(0xB1, 0, 2, 0)
        return "Returned to previous track"

    def _handle_audio_mute(self):
        # 0xAD is VK_VOLUME_MUTE
        self.user32.keybd_event(0xAD, 0, 0, 0)
        self.user32.keybd_event(0xAD, 0, 2, 0)
        return "Toggled volume mute"

    def _handle_audio_volume(self, change=0, level=None):
        if level is not None:
            # Setting exact volume requires Shell scripting or Pycaw. Let's use PowerShell inline:
            level = max(0, min(100, level))
            ps_cmd = f"(Get-WmiObject -Query 'Select * from Win32_Volume Where DriveLetter = \"C:\"').SetVolume({level})"
            subprocess.Popen(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL)
            return f"Set system volume to {level}%"
        
        # Volumes steps using keypresses (0xAF is VK_VOLUME_UP, 0xAE is VK_VOLUME_DOWN)
        key = 0xAF if change > 0 else 0xAE
        steps = abs(change) // 2
        for _ in range(steps):
            self.user32.keybd_event(key, 0, 0, 0)
            self.user32.keybd_event(key, 0, 2, 0)
        return f"Adjusted volume by {change}%"

    def _handle_launch_app(self, match):
        app_name = match.group(2)
        mapping = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "cmd": "cmd.exe",
            "paint": "mspaint.exe",
            "chrome": "chrome.exe",
            "browser": "explorer.exe http://www.google.com",
            "edge": "msedge.exe"
        }
        exe = mapping.get(app_name)
        if exe:
            subprocess.Popen(exe, shell=True)
            return f"Started {app_name}"
        return f"App {app_name} not configured"

    def _handle_screenshot(self):
        # Simulate pressing Windows+PrintScreen or call Snipping Tool
        # For prototype simplicity, run PSR (Problem Steps Recorder) or SnippingTool
        subprocess.Popen("snippingtool.exe", shell=True)
        return "Opened Snipping Tool for screenshot"

    def _handle_lock_screen(self):
        # LockWorkStation
        ctypes.windll.user32.LockWorkStation()
        return "Locked PC workstation"

    def _handle_shutdown(self):
        # Graceful shutdown command
        # subprocess.Popen("shutdown /s /t 60", shell=True)
        return "Shutdown requested (safely dry-runned in prototype)"

if __name__ == "__main__":
    router = TextToIntentRouter()
    
    # Test cases
    test_queries = [
        "please pause music",
        "skip track",
        "raise volume, it's too quiet",
        "set volume to 50%",
        "open notepad please",
        "lock my computer",
        "what time is it"
    ]
    
    for q in test_queries:
        matched, action = router.process_text(q)
        print(f"Query: '{q}' -> Matched: {matched} -> Action Result: {action}\n")
