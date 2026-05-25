"""
Unit tests for fullscreen application suppression helper.
"""
import pytest
from unittest.mock import Mock, patch
from platform_utils import FullscreenAppSuppressor

@pytest.mark.unit
def test_suppressor_no_ctypes():
    with patch('platform_utils.FullscreenAppSuppressor.__init__', return_value=None):
        suppressor = FullscreenAppSuppressor()
        suppressor.user32 = None
        suppressor.shell32 = None
        assert suppressor.is_fullscreen_app_active() is False

@pytest.mark.unit
def test_suppressor_shell32_busy():
    suppressor = FullscreenAppSuppressor()
    suppressor.user32 = Mock()
    suppressor.shell32 = Mock()
    
    # Mock SHQueryUserNotificationState to return QUNS_RUNNING_D3D_FULL_SCREEN (3)
    def mock_query(state_ref):
        state_ref.value = 3 # QUNS_RUNNING_D3D_FULL_SCREEN
        return 0 # S_OK
        
    suppressor.shell32.SHQueryUserNotificationState = mock_query
    
    # Patch byref globally in ctypes so local imports inside platform_utils receive the pointer-free patch
    with patch('ctypes.byref', lambda x: x):
        assert suppressor.is_fullscreen_app_active() is True

@pytest.mark.unit
def test_suppressor_window_bounds_check():
    suppressor = FullscreenAppSuppressor()
    suppressor.user32 = Mock()
    suppressor.shell32 = Mock()
    
    # S_FALSE or failed shell query
    suppressor.shell32.SHQueryUserNotificationState.return_value = 1 
    
    # Mock window handles
    suppressor.user32.GetForegroundWindow.return_value = 100
    suppressor.user32.GetDesktopWindow.return_value = 1
    suppressor.user32.GetShellWindow.return_value = 2
    
    # Mock screen resolution to 1920x1080
    def mock_get_metrics(metric_id):
        if metric_id == 0:
            return 1920
        elif metric_id == 1:
            return 1080
        return 0
    suppressor.user32.GetSystemMetrics = mock_get_metrics
    
    # Rect size matches screen
    def mock_get_rect(hwnd, rect_ref):
        rect_ref.left = 0
        rect_ref.top = 0
        rect_ref.right = 1920
        rect_ref.bottom = 1080
        return True
    suppressor.user32.GetWindowRect = mock_get_rect
    
    # Borderless window style check: style does not have WS_CAPTION
    # WS_CAPTION = 0x00C00000. Let's return 0x00000000 (no caption)
    suppressor.user32.GetWindowLongW.return_value = 0x00000000
    
    # Patch byref globally in ctypes so local imports inside platform_utils receive the pointer-free patch
    with patch('ctypes.byref', lambda x: x):
        assert suppressor.is_fullscreen_app_active() is True

@pytest.mark.unit
def test_suppressor_windowed_not_suppressed():
    suppressor = FullscreenAppSuppressor()
    suppressor.user32 = Mock()
    suppressor.shell32 = Mock()
    
    suppressor.shell32.SHQueryUserNotificationState.return_value = 1 
    suppressor.user32.GetForegroundWindow.return_value = 100
    suppressor.user32.GetDesktopWindow.return_value = 1
    suppressor.user32.GetShellWindow.return_value = 2
    
    # Normal windowed window size: 800x600
    def mock_get_rect(hwnd, rect_ref):
        rect_ref.left = 100
        rect_ref.top = 100
        rect_ref.right = 900
        rect_ref.bottom = 700
        return True
    suppressor.user32.GetWindowRect = mock_get_rect
    
    # Screen is 1920x1080
    suppressor.user32.GetSystemMetrics.side_effect = lambda x: 1920 if x == 0 else 1080
    
    with patch('ctypes.byref', lambda x: x):
        assert suppressor.is_fullscreen_app_active() is False
