"""
Flet-based transparent overlay for WinVE.
Replaces the broken pywebview + WPF overlay with native Flutter rendering.
"""
import flet as ft
import flet.canvas as cv
import asyncio
import json
import math
import logging
import ctypes

logger = logging.getLogger('haassist')

# State color palettes (same as old index.html)
STATE_COLORS = {
    'listening':   ['#00d2ff', '#7a00ff', '#ff007f', '#00e5ff', '#00d2ff'],
    'processing':  ['#00d2ff', '#7a00ff', '#ff007f', '#00e5ff', '#00d2ff'],
    'responding':  ['#00d2ff', '#7a00ff', '#ff007f', '#00e5ff', '#00d2ff'],
    'connecting':  ['#00d2ff', '#7a00ff', '#ff007f', '#00e5ff', '#00d2ff'],
    'success':     ['#0076ff', '#00c6ff', '#0052ff', '#00e5ff', '#0076ff'],
    'error':       ['#ff453a', '#ff9f0a', '#ff3b30', '#ff453a', '#ff453a'],
}

DEFAULT_COLORS = ['#00d2ff', '#7a00ff', '#ff007f', '#00e5ff', '#00d2ff']


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
        'angle': 0.0,
        'border_width': 4.0,
        'glow_width': 15.0,
        'colors': list(DEFAULT_COLORS),
        'active': False,
        # Audio reactivity
        'audio_buffer': [],
        'audio_baseline': 0.12,
        'audio_max': 0.45,
        'audio_history': [],
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

        # Screen dimensions
        w = page.width if (page.width and page.width > 0) else (page.window.width or screen_w)
        h = page.height if (page.height and page.height > 0) else (page.window.height or screen_h)

        # Inset boundaries to prevent clipping
        border_inset = 6.0
        glow_inset = 12.0

        # --- Paint builders ---
        def border_paint(angle, width, colors):
            return ft.Paint(
                stroke_width=width,
                style=ft.PaintingStyle.STROKE,
                gradient=ft.PaintSweepGradient(
                    center=ft.Offset(w / 2, h / 2),
                    start_angle=angle,
                    end_angle=angle + math.pi * 2,
                    colors=colors,
                ),
            )

        def glow_paint(angle, width, colors):
            # Glow: wider stroke, same gradient
            return ft.Paint(
                stroke_width=width,
                style=ft.PaintingStyle.STROKE,
                gradient=ft.PaintSweepGradient(
                    center=ft.Offset(w / 2, h / 2),
                    start_angle=angle,
                    end_angle=angle + math.pi * 2,
                    colors=colors,
                ),
            )

        # --- Canvas shapes ---
        glow_rect = cv.Rect(
            x=glow_inset, y=glow_inset, width=w - glow_inset * 2, height=h - glow_inset * 2,
            paint=glow_paint(0, 15, state['colors']),
        )
        border_rect = cv.Rect(
            x=border_inset, y=border_inset, width=w - border_inset * 2, height=h - border_inset * 2,
            paint=border_paint(0, 4, state['colors']),
        )

        canvas = cv.Canvas(
            [glow_rect, border_rect],
            width=w, height=h,
            left=0, top=0, right=0, bottom=0,
            expand=True,
        )

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
                canvas,
                ft.Container(
                    content=ft.Column(
                        [error_card, success_card, response_card],
                        alignment=ft.MainAxisAlignment.END,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.alignment.bottom_center,
                    padding=ft.padding.only(bottom=60),
                    width=w,
                    height=h,
                ),
            ], width=w, height=h)
        )

        # --- Audio processing (same algo as old index.html) ---
        def process_audio(fft_data):
            if not fft_data:
                return 0
            avg = 0.0
            count = 0.0
            relevant = min(len(fft_data), 18)
            for i in range(relevant):
                weight = (relevant - i) / relevant
                avg += fft_data[i] * weight
                count += weight
            if count <= 0:
                return 0
            raw = avg / count

            state['audio_history'].append(raw)
            if len(state['audio_history']) > 100:
                state['audio_history'].pop(0)

            if len(state['audio_history']) > 15:
                sorted_h = sorted(state['audio_history'])
                bi = int(len(sorted_h) * 0.15)
                mi = int(len(sorted_h) * 0.92)
                state['audio_baseline'] = state['audio_baseline'] * 0.95 + sorted_h[bi] * 0.05
                state['audio_max'] = state['audio_max'] * 0.95 + sorted_h[mi] * 0.05
                state['audio_baseline'] = max(0.04, state['audio_baseline'])
                state['audio_max'] = max(state['audio_baseline'] * 1.6, state['audio_max'])

            capped = min(raw, state['audio_max'])
            rng = state['audio_max'] - state['audio_baseline']
            if rng <= 0:
                normalized = 0
            elif capped < state['audio_baseline']:
                normalized = max(0, (capped / state['audio_baseline']) * 0.08)
            else:
                normalized = 0.08 + 0.92 * (capped - state['audio_baseline']) / rng

            state['audio_buffer'].append(normalized)
            if len(state['audio_buffer']) > 4:
                state['audio_buffer'].pop(0)
            return sum(state['audio_buffer']) / len(state['audio_buffer'])

        # --- State change handler ---
        def handle_state_change(new_state, data):
            if new_state == state['current'] and not data.get('errorMessage') and not data.get('successMessage'):
                return

            state['current'] = new_state
            state['colors'] = STATE_COLORS.get(new_state, list(DEFAULT_COLORS))

            # Reset cards
            error_card.visible = False
            success_card.visible = False
            # Reset success card color back to default blue
            success_text.color = "#0a84ff"
            success_card.border = ft.border.all(1, ft.Colors.with_opacity(0.35, "#0a84ff"))

            if new_state == 'hidden':
                response_card.visible = False
                state['active'] = False
                state['border_width'] = 4.0
                state['glow_width'] = 15.0
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

        # --- Animation loop (~30 FPS) ---
        async def animate():
            nonlocal w, h
            while True:
                # Update dimensions dynamically if page size changes
                nw = page.width if (page.width and page.width > 0) else (page.window.width or w)
                nh = page.height if (page.height and page.height > 0) else (page.window.height or h)
                if nw != w or nh != h:
                    w, h = nw, nh
                    border_rect.width = w - border_inset * 2
                    border_rect.height = h - border_inset * 2
                    glow_rect.width = w - glow_inset * 2
                    glow_rect.height = h - glow_inset * 2
                    canvas.width = w
                    canvas.height = h

                if state['active']:
                    state['angle'] += 0.05
                    if state['angle'] > 628:  # ~100 full rotations, reset
                        state['angle'] = 0

                    bw = state['border_width']
                    gw = state['glow_width']
                    c = state['colors']
                    a = state['angle']

                    border_rect.paint = border_paint(a, bw, c)
                    glow_rect.paint = glow_paint(a, gw, c)

                    try:
                        canvas.update()
                    except Exception:
                        pass

                await asyncio.sleep(1 / 30)

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
                                elif t == "audio_data":
                                    fft = data.get("fft", [])
                                    level = process_audio(fft)
                                    if state['current'] in ('listening', 'responding'):
                                        state['border_width'] = 4 + level * 10
                                        state['glow_width'] = 15 + level * 25
                                    else:
                                        state['border_width'] = 4
                                        state['glow_width'] = 15
                                elif t == "response_text":
                                    handle_response_text(data.get("text", ""))
                            except json.JSONDecodeError:
                                pass
                except Exception as e:
                    logger.debug(f"Overlay WS reconnecting: {e}")
                    await asyncio.sleep(2)

        # --- Handle window resize ---
        def on_resize(e):
            nonlocal w, h
            nw = page.width if (page.width and page.width > 0) else (page.window.width or w)
            nh = page.height if (page.height and page.height > 0) else (page.window.height or h)
            if nw != w or nh != h:
                w, h = nw, nh
                border_rect.width = w - border_inset * 2
                border_rect.height = h - border_inset * 2
                glow_rect.width = w - glow_inset * 2
                glow_rect.height = h - glow_inset * 2
                canvas.width = w
                canvas.height = h

        page.on_resized = on_resize

        # Launch background tasks
        page.run_task(animate)
        page.run_task(ws_listen)

    ft.app(target=main)
