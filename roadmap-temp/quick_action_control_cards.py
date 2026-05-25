"""
Prototype Implementation: Quick-Action Control Cards
Stored in roadmap-temp/ for reference and future integration.
"""
import flet as ft
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_control_cards")

class QuickActionControlCard:
    """Renders temporary glassmorphic widgets for physical override after voice commands."""
    
    def __init__(self):
        self.container = None
        self.control_area = None
        self.hide_task = None

    def build_card(self) -> ft.Control:
        """Construct the container for quick actions."""
        self.control_area = ft.Column(spacing=10, tight=True)
        
        self.container = ft.Container(
            content=self.control_area,
            padding=15,
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
            border=ft.border.all(1, ft.Colors.with_opacity(0.25, ft.Colors.WHITE)),
            blur=ft.Blur(15, 15, ft.BlurStyle.OUTER),
            width=380,
            visible=False,
            margin=ft.margin.only(bottom=150) # Positioned center-right above border
        )
        return self.container

    async def show_light_controls(self, page: ft.Page, entity_name: str, brightness: int, state: bool, client_callback):
        """Display a brightness slider and toggle for a light entity."""
        logger.info(f"Showing controls for light {entity_name}")
        
        # Cancel any pending auto-hide timer
        if self.hide_task:
            self.hide_task.cancel()
            
        self.control_area.controls.clear()
        
        # Header title
        title = ft.Text(f"💡 {entity_name}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        
        # Toggle Switch
        light_switch = ft.Switch(
            value=state,
            label="On" if state else "Off",
            label_style=ft.TextStyle(color=ft.Colors.WHITE),
            on_change=lambda e: self._on_toggle_change(light_switch, slider, client_callback, entity_name)
        )
        
        # Brightness Slider
        slider = ft.Slider(
            min=0,
            max=100,
            divisions=10,
            value=brightness,
            label="{value}%",
            disabled=not state,
            on_change=lambda e: self._on_slider_change(slider, client_callback, entity_name)
        )
        
        self.control_area.controls.extend([
            title,
            ft.Row([light_switch], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Column([
                ft.Text("Brightness", size=12, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                slider
            ], spacing=2)
        ])
        
        self.container.visible = True
        page.update()
        
        # Auto-hide after 8 seconds of inactivity
        self.hide_task = asyncio.create_task(self._auto_hide_delay(page, 8))

    async def show_media_controls(self, page: ft.Page, entity_name: str, volume: float, state: str, client_callback):
        """Display play/pause control and volume slider for media player."""
        logger.info(f"Showing controls for media player {entity_name}")
        
        if self.hide_task:
            self.hide_task.cancel()
            
        self.control_area.controls.clear()
        
        title = ft.Text(f"🎵 {entity_name}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        
        play_pause_button = ft.IconButton(
            icon=ft.Icons.PAUSE_ROUNDED if state == "playing" else ft.Icons.PLAY_ARROW_ROUNDED,
            icon_color=ft.Colors.WHITE,
            on_click=lambda e: self._on_media_toggle(play_pause_button, entity_name, client_callback)
        )
        
        volume_slider = ft.Slider(
            min=0,
            max=100,
            value=int(volume * 100),
            on_change=lambda e: self._on_volume_change(volume_slider, entity_name, client_callback)
        )
        
        self.control_area.controls.extend([
            title,
            ft.Row([
                ft.Text(state.capitalize(), color=ft.Colors.WHITE),
                play_pause_button
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Column([
                ft.Text("Volume", size=12, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                volume_slider
            ], spacing=2)
        ])
        
        self.container.visible = True
        page.update()
        
        self.hide_task = asyncio.create_task(self._auto_hide_delay(page, 8))

    def _on_toggle_change(self, switch_ctrl, slider_ctrl, callback, entity_id):
        """Handles switch toggling."""
        state = switch_ctrl.value
        switch_ctrl.label = "On" if state else "Off"
        slider_ctrl.disabled = not state
        callback(entity_id, "turn_on" if state else "turn_off")
        
    def _on_slider_change(self, slider_ctrl, callback, entity_id):
        """Handles brightness slider change."""
        brightness_val = int(slider_ctrl.value)
        callback(entity_id, "turn_on", brightness=brightness_val)

    def _on_media_toggle(self, btn, entity_id, callback):
        """Handles play/pause click."""
        is_playing = btn.icon == ft.Icons.PAUSE_ROUNDED
        btn.icon = ft.Icons.PLAY_ARROW_ROUNDED if is_playing else ft.Icons.PAUSE_ROUNDED
        callback(entity_id, "media_pause" if is_playing else "media_play")

    def _on_volume_change(self, slider, entity_id, callback):
        """Handles media volume slider change."""
        vol_fraction = slider.value / 100.0
        callback(entity_id, "set_volume", volume=vol_fraction)

    async def _auto_hide_delay(self, page: ft.Page, delay_seconds: int):
        """Waits and then hides the quick action card."""
        try:
            await asyncio.sleep(delay_seconds)
            self.container.visible = False
            page.update()
            logger.info("Quick action control card auto-hidden.")
        except asyncio.CancelledError:
            pass
