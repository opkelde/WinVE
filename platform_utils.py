"""
Utility functions for WinVE.
"""
import os
import sys
import platform
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger('haassist')

def get_icon_path():
    """Get appropriate icon path for current platform."""
    base_path = Path(__file__).parent / 'img'
    
    ico_path = base_path / 'icon.ico'
    if ico_path.exists():
        return str(ico_path)
    return None

def hide_window_from_taskbar(window_title="WinVE"):
    """Hide window from taskbar - Windows-only implementation."""
    return _hide_from_taskbar_windows(window_title)

def _hide_from_taskbar_windows(window_title):
    """Windows-specific taskbar hiding and transparency configuration using ctypes."""
    try:
        import ctypes
        from ctypes import wintypes
        
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int),
                ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int),
                ("cyBottomHeight", ctypes.c_int),
            ]
            
        user32 = ctypes.windll.user32
        found_windows = []
        
        def enum_windows_proc(hwnd, lParam):
            window_text = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, window_text, 512)
            class_name = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetClassNameW(hwnd, class_name, 512)
            
            # Check for matching window title
            if window_text.value == window_title:
                found_windows.append((hwnd, window_text.value, class_name.value))

                # Extend DWM frame into client area for true glass/transparent rendering
                try:
                    dwmapi = ctypes.windll.dwmapi
                    margins = MARGINS(-1, -1, -1, -1)
                    dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
                    logger.info(f"DWM extended frame into client area for hwnd: {hwnd}")
                except Exception as dwm_err:
                    logger.warning(f"Failed to extend DWM frame: {dwm_err}")

                GWL_EXSTYLE = -20
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_APPWINDOW = 0x00040000
                WS_EX_LAYERED = 0x00080000
                WS_EX_TRANSPARENT = 0x00000020

                current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                new_style = (current_style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW | WS_EX_LAYERED | WS_EX_TRANSPARENT
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
                
                SWP_FRAMECHANGED = 0x0020
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                
                # Apply styles without resizing or moving the window (retains fullscreen)
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0,
                    0, 0,
                    0, 0,
                    SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOMOVE | SWP_NOSIZE
                )
                
                logger.info(f"Window hidden from taskbar and made click-through: '{window_text.value}'")
            
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_windows_proc), 0)
        
        return len(found_windows) > 0
        
    except Exception as e:
        logger.error(f"Windows taskbar hiding failed: {e}")
        return False

def open_file_manager(path):
    """Open file manager at specified path - Windows-only implementation."""
    try:
        import locale
        system_encoding = locale.getpreferredencoding()
        
        # On Windows, use CREATE_NO_WINDOW to avoid console pop-ups
        subprocess.run(['explorer', str(path)], 
                      creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                      encoding=system_encoding)
        return True
    except UnicodeEncodeError as e:
        logger.error(f"Unicode error opening path {path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to open file manager: {e}")
        return False

def check_wake_word_noise_suppression():
    """Check if noise suppression is available for wake word detection."""
    # Disabled on Windows due to compatibility issues
    return False