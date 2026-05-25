"""
Fullscreen Application Text Suppression for WinVE.
Monitors Windows shell state and foreground windows to detect when a fullscreen 
game or application is active, automatically suppressing HUD overlays, 
listening animations, and response texts to prevent visual disruption.
"""
import ctypes
from ctypes import wintypes
import time

class FullscreenAppSuppressor:
    """Detects active fullscreen applications and manages HUD visibility state."""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.shell32 = ctypes.windll.shell32
        
        # Query User Notification State constants
        self.QUNS_NOT_PRESENT = 1
        self.QUNS_BUSY = 2
        self.QUNS_RUNNING_D3D_FULL_SCREEN = 3
        self.QUNS_PRESENTATION_MODE = 4
        self.QUNS_ACCEPTS_NOTIFICATIONS = 5
        self.QUNS_QUIET_TIME = 6
        self.QUNS_APP = 7

        # Settings flag
        self.suppress_enabled = True

    def is_fullscreen_app_active(self):
        """
        Determines if a fullscreen application is active.
        Combines shell notification queries and active window dimension checks.
        """
        if not self.suppress_enabled:
            return False

        # Method 1: Query Shell User Notification State
        # Highly reliable for detecting Direct3D fullscreen games, PowerPoint, etc.
        state = ctypes.c_int(0)
        hr = self.shell32.SHQueryUserNotificationState(ctypes.byref(state))
        if hr == 0:  # S_OK
            if state.value in (self.QUNS_RUNNING_D3D_FULL_SCREEN, self.QUNS_BUSY, self.QUNS_PRESENTATION_MODE):
                return True

        # Method 2: Active Window size check (Fallback for non-D3D borderless windows)
        hwnd = self.user32.GetForegroundWindow()
        if hwnd:
            # Skip checking Desktop or Taskbar
            desktop_hwnd = self.user32.GetDesktopWindow()
            shell_hwnd = self.user32.GetShellWindow()
            if hwnd in (desktop_hwnd, shell_hwnd):
                return False

            rect = wintypes.RECT()
            if self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                
                # Get current monitor size
                screen_width = self.user32.GetSystemMetrics(0) # SM_CXSCREEN
                screen_height = self.user32.GetSystemMetrics(1) # SM_CYSCREEN
                
                # If active window dimensions match or exceed the primary screen bounds, it is fullscreen
                if width >= screen_width and height >= screen_height:
                    # Double check window styles
                    GWL_STYLE = -16
                    WS_MAXIMIZE = 0x01000000
                    style = self.user32.GetWindowLongW(hwnd, GWL_STYLE)
                    
                    # If it is maximized but has normal borders, it is not fullscreen
                    # A borderless fullscreen window lacks WS_CAPTION (0x00C00000) or WS_THICKFRAME (0x00040000)
                    WS_CAPTION = 0x00C00000
                    if not (style & WS_CAPTION):
                        return True
                        
        return False

    def evaluate_hud_visibility(self, default_visibility=True):
        """
        Applies logic to decide if HUD text should be displayed.
        Returns False if suppressed, otherwise returns the default requested state.
        """
        if self.is_fullscreen_app_active():
            print("🚫 Suppress Overlay: Fullscreen application detected. HUD elements hidden.")
            return False
        return default_visibility

if __name__ == "__main__":
    suppressor = FullscreenAppSuppressor()
    
    print("🖥️ Fullscreen Suppressor Monitor active. Run a fullscreen game or press F11 in browser.")
    print("Monitoring status every 2 seconds (Ctrl+C to stop)...\n")
    
    try:
        last_state = None
        while True:
            is_fs = suppressor.is_fullscreen_app_active()
            hud_visible = suppressor.evaluate_hud_visibility(default_visibility=True)
            
            if is_fs != last_state:
                status = "🔴 FULLSCREEN (HUD Suppressed)" if is_fs else "🟢 Windowed (HUD Active)"
                print(f"[{time.strftime('%H:%M:%S')}] State Change: {status}")
                last_state = is_fs
                
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
