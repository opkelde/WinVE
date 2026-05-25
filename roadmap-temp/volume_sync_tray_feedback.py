"""
Prototype Implementation: System Tray Volume Control & Status Sync
Stored in roadmap-temp/ for reference and future integration.
"""
import pystray
from PIL import Image
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_tray_sync")

class TrayFeedbackManager:
    """Manages the status of the system tray menu, icon tooltips, and volume controls."""
    
    def __init__(self, main_app=None):
        self.main_app = main_app
        self.tray_icon = None
        self.muted = False
        self.volume = 100 # Default output volume (0-100)
        self.connection_status = "Disconnected"

    def create_menu(self) -> pystray.Menu:
        """Construct the tray menu with volume slider items and dynamic connection state."""
        
        # Helper menu item builders
        def get_mute_label(item):
            return "🔊 Mute Microphone" if not self.muted else "🔇 Unmute Microphone"
            
        def get_volume_label(item):
            return f"🔈 Output Volume: {self.volume}%"

        def get_status_label(item):
            return f"🌐 Status: {self.connection_status}"

        # Setup items
        menu = pystray.Menu(
            pystray.MenuItem(get_status_label, action=None, enabled=False),
            pystray.MenuItem(get_volume_label, action=None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(get_mute_label, self.toggle_mute),
            pystray.MenuItem("➕ Increase Volume", lambda: self.adjust_volume(10)),
            pystray.MenuItem("➖ Decrease Volume", lambda: self.adjust_volume(-10)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️ Settings", self.open_settings),
            pystray.MenuItem("❌ Exit", self.exit_app)
        )
        return menu

    def setup_tray(self):
        """Initialize the tray icon with dynamic tooltip matching active pipeline status."""
        icon_path = os.path.join(os.path.dirname(__file__), "..", "img", "icon.ico")
        if os.path.exists(icon_path):
            img = Image.open(icon_path)
        else:
            # Fallback mock image
            img = Image.new("RGB", (16, 16), "blue")
            
        self.tray_icon = pystray.Icon(
            "WinVE",
            img,
            menu=self.create_menu(),
            title=f"WinVE - {self.connection_status} (Vol: {self.volume}%)"
        )
        
        # Run tray loop in background thread
        # self.tray_icon.run_detached()

    def update_connection_status(self, status: str):
        """Update system tray state description."""
        logger.info(f"Tray status sync: {status}")
        self.connection_status = status
        
        if self.tray_icon:
            # Update system tooltip
            self.tray_icon.title = f"WinVE - {status} (Vol: {self.volume}%)"
            # Redraw menu items
            self.tray_icon.update_menu()

    def adjust_volume(self, delta: int):
        """Adjust output volume level and update tray."""
        self.volume = max(0, min(100, self.volume + delta))
        logger.info(f"Output volume adjusted to: {self.volume}%")
        
        if self.tray_icon:
            self.tray_icon.title = f"WinVE - {self.connection_status} (Vol: {self.volume}%)"
            self.tray_icon.update_menu()
            
        # Update audio player gain in main loop
        if self.main_app and hasattr(self.main_app, "audio_manager"):
            self.main_app.audio_manager.set_output_volume(self.volume / 100.0)

    def toggle_mute(self, item):
        """Toggles microphone capturing state."""
        self.muted = not self.muted
        logger.info(f"Microphone mute status: {self.muted}")
        
        if self.tray_icon:
            self.tray_icon.update_menu()
            
        # Notify the active audio engine to pause recording
        if self.main_app:
            if self.muted:
                self.main_app.pause_wake_word_detection()
            else:
                self.main_app.resume_wake_word_detection()

    def open_settings(self):
        if self.main_app:
            self.main_app.open_settings()

    def exit_app(self):
        if self.main_app:
            self.main_app.exit()
        if self.tray_icon:
            self.tray_icon.stop()
