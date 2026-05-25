"""
Prototype Implementation: Local PC Voice Commands & Dedicated Offline Mode
Stored in roadmap-temp/ for reference and future integration.
"""
import os
import sys
import subprocess
import threading
import logging

# Mock logging setup matching winve structure
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_offline_mode")

class OfflinePCCommandHandler:
    """Handles local automation commands when offline or in PC-control mode."""
    
    def __init__(self):
        # Dictionary mapping trigger phrases to execution functions
        self.commands = {
            "lock pc": self.lock_computer,
            "lock computer": self.lock_computer,
            "open notepad": lambda: self.open_app("notepad.exe"),
            "open calculator": lambda: self.open_app("calc.exe"),
            "take screenshot": self.take_screenshot,
            "mute volume": lambda: self.adjust_volume("mute"),
            "unmute volume": lambda: self.adjust_volume("unmute"),
        }

    def execute_command(self, text: str) -> bool:
        """Parse spoken text and execute match if found."""
        cleaned_text = text.lower().strip()
        for phrase, func in self.commands.items():
            if phrase in cleaned_text:
                logger.info(f"Offline Command Matched: '{phrase}' -> executing...")
                try:
                    func()
                    return True
                except Exception as e:
                    logger.error(f"Error executing offline command '{phrase}': {e}")
                    return False
        logger.info(f"No offline command matched for: '{text}'")
        return False

    def lock_computer(self):
        """Lock the Windows workstation using rundll32."""
        logger.info("Locking workstation...")
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)

    def open_app(self, app_name: str):
        """Open a standard Windows application."""
        logger.info(f"Opening application: {app_name}")
        # Run disconnected so it doesn't block the assistant process
        subprocess.Popen([app_name], start_new_session=True)

    def take_screenshot(self):
        """Take screenshot and save to user's Pictures folder."""
        logger.info("Taking screenshot...")
        try:
            from PIL import ImageGrab
            import datetime
            pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(pictures_dir, f"WinVE_Screenshot_{timestamp}.png")
            
            # Capture the entire screen
            screenshot = ImageGrab.grab()
            screenshot.save(filepath)
            logger.info(f"Screenshot saved to: {filepath}")
        except ImportError:
            logger.error("PIL (Pillow) library is required to take screenshots!")

    def adjust_volume(self, action: str):
        """Adjust Windows system volume via simple nircmd or powershell."""
        # Prototype using powershell audio management or similar
        logger.info(f"Adjusting volume: {action}")
        if action == "mute":
            # Command to mute system volume
            cmd = "$wsh = New-Object -ComObject Wscript.Shell; $wsh.SendKeys([char]173)"
            subprocess.run(["powershell", "-Command", cmd], check=True)
        elif action == "unmute":
            # Toggle mute/unmute
            cmd = "$wsh = New-Object -ComObject Wscript.Shell; $wsh.SendKeys([char]173)"
            subprocess.run(["powershell", "-Command", cmd], check=True)


class ModeOrchestrator:
    """Manages active mode (Home Assistant satellite vs Offline Local PC control)."""
    
    def __init__(self, main_app=None):
        self.main_app = main_app
        self.active_mode = "home_assistant"  # or "offline_pc"
        
        # Configuration for dedicated keybinds/wake words
        self.configs = {
            "home_assistant": {
                "hotkey": "ctrl+shift+h",
                "wake_words": ["computer_v2"],
            },
            "offline_pc": {
                "hotkey": "ctrl+shift+p",
                "wake_words": ["jarvis_v2"],
            }
        }
        
    def set_mode(self, mode: str):
        """Swap active hotkey listeners and wake words for the target mode."""
        if mode not in self.configs:
            logger.warning(f"Invalid mode requested: {mode}")
            return
            
        logger.info(f"Switching mode: {self.active_mode} -> {mode}")
        self.active_mode = mode
        
        # In actual integration:
        # 1. Unregister old hotkey listener
        # 2. Register new hotkey (e.g. ctrl+shift+p)
        # 3. Reload wake word detector with the dedicated model list (e.g. jarvis_v2)
        self._apply_mode_bindings()

    def _apply_mode_bindings(self):
        config = self.configs[self.active_mode]
        logger.info(f"Active Hotkey: {config['hotkey']}")
        logger.info(f"Active Wake Words: {config['wake_words']}")
        # Call wake word detector reload and keyboard hotkey rebind here
