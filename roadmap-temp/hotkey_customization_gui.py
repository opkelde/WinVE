"""
Prototype Implementation: Custom Hotkey/Shortcut Bindings GUI
Stored in roadmap-temp/ for reference and future integration.
"""
import flet as ft
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_hotkey_gui")

class HotkeyCustomizerGUI:
    """Provides a settings interface for registering custom keyboard trigger shortcuts."""
    
    def __init__(self):
        self.shortcut_field = None
        self.is_recording = False
        self.recorded_keys = set()
        self.selected_action = "activate_ha"

    def build_widget(self, page: ft.Page) -> ft.Control:
        """Build the hotkey customization card with a recording indicator."""
        
        self.shortcut_field = ft.TextField(
            label="Active Shortcut Bind",
            value="Ctrl+Shift+H",
            read_only=True,
            width=250,
            text_align=ft.TextAlign.CENTER
        )
        
        record_button = ft.ElevatedButton(
            "Record Hotkey",
            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT_ROUNDED,
            on_click=lambda e: self._start_recording(page)
        )
        
        action_dropdown = ft.Dropdown(
            label="Trigger Action",
            value=self.selected_action,
            options=[
                ft.dropdown.Option("activate_ha", "🎙️ Trigger Home Assistant Assist"),
                ft.dropdown.Option("activate_offline", "💻 Trigger Offline PC Assistant"),
                ft.dropdown.Option("toggle_mute", "🔇 Toggle Wake Word Mute"),
                ft.dropdown.Option("show_hud", "📺 Open Settings Window")
            ]
        )

        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("⌨️ Shortcut Customization", size=16, weight=ft.FontWeight.BOLD),
                        ft.Text("Define custom global keyboard combinations to trigger assistant actions.", size=12),
                        ft.Row([
                            self.shortcut_field,
                            record_button
                        ], spacing=10),
                        action_dropdown
                    ],
                    spacing=12
                ),
                padding=15
            )
        )

    def _start_recording(self, page: ft.Page):
        """Starts keyboard capturing listener."""
        self.is_recording = True
        self.recorded_keys.clear()
        self.shortcut_field.value = "Press keys..."
        self.shortcut_field.color = ft.Colors.RED_ACCENT
        page.update()
        
        # In full implementation:
        # hook into the keyboard library globally
        # keyboard.hook(self._on_key_event)
        logger.info("Recording global hotkey...")

    def _on_key_event(self, event, page: ft.Page):
        """Processes global keyboard hook events."""
        if not self.is_recording:
            return
            
        # Add key to recorded set
        name = event.name.lower()
        if event.event_type == "down":
            self.recorded_keys.add(name)
            self.shortcut_field.value = "+".join(sorted(list(self.recorded_keys))).upper()
            page.update()
        elif event.event_type == "up":
            # Finish recording when modifier keys are released
            self.is_recording = False
            # keyboard.unhook(self._on_key_event)
            self.shortcut_field.color = ft.Colors.WHITE
            page.update()
            logger.info(f"Hotkey recorded: {self.shortcut_field.value}")
