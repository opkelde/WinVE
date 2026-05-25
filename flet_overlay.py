"""
Flet-based transparent overlay for WinVE.
Replaces the broken pywebview + WPF overlay with native Flutter rendering.
"""
import flet as ft
import asyncio
import json
import ctypes
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger('haassist')

def get_env_bool(key, default=False):
    """Get environment variable as boolean with safe parsing from .env without loading utils."""
    try:
        import sys
        if getattr(sys, 'frozen', False):
            env_path = os.path.join(os.path.dirname(sys.executable), '.env')
        else:
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            
        value = os.getenv(key)
        if value is None:
            return default
            
        return value.lower() in ('true', '1', 'yes', 'y', 't')
    except Exception:
        return default


def run_overlay(port=8765):
    """Launch the Flet overlay window. Blocks until closed."""

    # Query true screen dimensions on Windows thread-safely
    try:
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
    except Exception:
        screen_w = 1920
        screen_h = 1080

    # Shared mutable state
    state = {
        'current': 'hidden',
        'active': False,
    }

    def main(page: ft.Page):
        # --- Window setup: transparent, frameless, click-through ---
        page.window.frameless = True
        page.window.bgcolor = ft.Colors.TRANSPARENT
        page.window.always_on_top = True
        page.window.full_screen = True
        page.window.skip_task_bar = True
        page.window.ignore_mouse_events = True
        page.window.shadow = False
        page.window.visible = False  # start hidden
        page.window.width = screen_w
        page.window.height = screen_h
        page.bgcolor = ft.Colors.TRANSPARENT
        page.padding = 0
        page.spacing = 0
        page.update()

        # --- Text cards (glassmorphic) ---
        error_text = ft.Text("", size=15, weight=ft.FontWeight.W_500, color="#ff453a")
        error_card = ft.Container(
            content=error_text,
            bgcolor=ft.Colors.with_opacity(0.8, "#0A0A0F"),
            border_radius=16,
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            shadow=ft.BoxShadow(blur_radius=40, color=ft.Colors.with_opacity(0.6, ft.Colors.BLACK)),
            border=ft.border.all(1, ft.Colors.with_opacity(0.35, "#ff453a")),
            visible=False,
        )

        success_text = ft.Text("", size=15, weight=ft.FontWeight.W_500, color="#0a84ff")
        success_card = ft.Container(
            content=success_text,
            bgcolor=ft.Colors.with_opacity(0.8, "#0A0A0F"),
            border_radius=16,
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            shadow=ft.BoxShadow(blur_radius=40, color=ft.Colors.with_opacity(0.6, ft.Colors.BLACK)),
            border=ft.border.all(1, ft.Colors.with_opacity(0.35, "#0a84ff")),
            visible=False,
        )

        response_text_ctrl = ft.Text("", size=16, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE)
        response_card = ft.Container(
            content=response_text_ctrl,
            bgcolor=ft.Colors.with_opacity(0.8, "#0A0A0F"),
            border_radius=16,
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
            shadow=ft.BoxShadow(blur_radius=40, color=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)),
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
            visible=False,
        )

        # --- Layout ---
        page.add(
            ft.Stack([
                ft.Container(
                    content=ft.Column(
                        [error_card, success_card, response_card],
                        alignment=ft.MainAxisAlignment.END,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.alignment.bottom_center,
                    padding=ft.padding.only(bottom=60),
                    left=0,
                    top=0,
                    right=0,
                    bottom=0,
                ),
            ], expand=True)
        )

        # --- State change handler ---
        def handle_state_change(new_state, data):
            if new_state == state['current'] and not data.get('errorMessage') and not data.get('successMessage'):
                return

            state['current'] = new_state

            # Reset cards
            error_card.visible = False
            success_card.visible = False
            # Reset success card color back to default blue
            success_text.color = "#0a84ff"
            success_card.border = ft.border.all(1, ft.Colors.with_opacity(0.35, "#0a84ff"))

            if new_state == 'hidden':
                response_card.visible = False
                state['active'] = False
                page.window.visible = False
                page.update()
                return

            state['active'] = True
            page.window.visible = True

            if new_state == 'error' and data.get('errorMessage'):
                error_text.value = data['errorMessage']
                error_card.visible = True
            elif new_state == 'success':
                success_text.value = data.get('successMessage', 'Success')
                success_card.visible = True
            elif new_state == 'connecting':
                success_text.value = data.get('successMessage', 'Connecting...')
                success_text.color = '#ffeb3b'
                success_card.border = ft.border.all(1, ft.Colors.with_opacity(0.35, '#ffeb3b'))
                success_card.visible = True

            if new_state == 'listening':
                if get_env_bool('HA_SHOW_LISTENING_INDICATOR', True):
                    response_text_ctrl.value = "Listening..."
                    response_card.visible = True
            elif new_state != 'responding' and response_text_ctrl.value == "Listening...":
                response_card.visible = False

            page.update()

        def handle_response_text(text):
            if text:
                response_text_ctrl.value = text
                response_card.visible = True
            else:
                response_card.visible = False
            try:
                page.update()
            except Exception:
                pass

        # --- WebSocket listener ---
        async def ws_listen():
            import websockets
            while True:
                try:
                    async with websockets.connect(f"ws://localhost:{port}") as ws:
                        await ws.send(json.dumps({"type": "ready"}))
                        logger.info("Overlay connected to animation server")
                        async for raw in ws:
                            try:
                                data = json.loads(raw)
                                t = data.get("type")
                                if t == "state_change":
                                    handle_state_change(data.get("state", "hidden"), data)
                                elif t == "response_text":
                                    handle_response_text(data.get("text", ""))
                            except json.JSONDecodeError:
                                pass
                except Exception as e:
                    logger.debug(f"Overlay WS reconnecting: {e}")
                    await asyncio.sleep(2)

        # Launch background tasks
        page.run_task(ws_listen)

    ft.app(target=main)
