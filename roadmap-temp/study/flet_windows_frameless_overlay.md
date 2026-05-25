# Flet Windows Frameless Overlay & Transparency

## Overview
WinVE uses Flet (which sits on top of Flutter) to build desktop settings interfaces and visual HUD overlays. Displaying a translucent, floating, borderless voice listening ring requires configuring Flet to bypass the standard operating system window decorations and enabling click-through properties.

## Window Configurations in Flet
Flet allows modifying window behaviors via properties on the `Page` object or calling specific Win32 hooks.

### 1. Frameless and Transparent Setup
To construct an overlay, Flet requires the window to be stripped of its border, title bar, and background color:
```python
page.window_bgcolor = ft.colors.TRANSPARENT
page.bgcolor = ft.colors.TRANSPARENT
page.window_title_bar_hidden = True
page.window_frameless = True
```
- **`window_title_bar_hidden` & `window_frameless`**: Removes standard OS frame, close/minimize buttons, and window resizing borders.
- **`window_bgcolor` & `bgcolor`**: Set to transparent, forcing the webview/canvas surface to render with an alpha channel.

### 2. Window Position and Top-Most State
An overlay must sit above other applications without stealing active keyboard focus unless requested:
```python
page.window_always_on_top = True
page.window_skip_task_bar = True  # Hide from alt-tab and system taskbar
page.window_focused = False       # Run in background
```

## Win32 API Tweaks (Via ctypes)
While Flet sets base transparency, dynamic click-through behavior (so click events pass through the transparent sections of the HUD to the application underneath) requires direct invocation of `user32.dll`.

### Making the Window Click-Through (WS_EX_TRANSPARENT)
To allow clicking through transparent parts of the UI, you must manipulate the window's Extended Styles (`GWL_EXSTYLE`):

```python
import ctypes
from ctypes import wintypes

# Find the window handle of our Flet window
hwnd = ctypes.windll.user32.FindWindowW(None, "WinVE Overlay")

# Constants
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

# Get current styles
style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

# Apply layered and transparent styles
new_style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT
ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
```
- **`WS_EX_LAYERED`**: Enables alpha blending and transparency mapping for the window.
- **`WS_EX_TRANSPARENT`**: Informs the OS that hit-testing should ignore this window, allowing clicks to drop down to whatever is underneath.

### Restoring Interaction
To toggle settings or let users click on cards, remove the `WS_EX_TRANSPARENT` flag:
```python
new_style = style & ~WS_EX_TRANSPARENT
ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
```

## Caveats and Limitations
1. **Flashes on Load**: On older Windows versions (or machines with slow graphic drivers), Webview2 can momentarily flash a grey/white square on window initialization. Setting the registry default for WebView2 theme or initializing invisible and fading in is a common workaround.
2. **Hitboxes**: Multi-monitor setups require explicit mapping of coordinates, as virtual desktop coordinates can be negative on secondary screens.
