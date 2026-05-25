"""
Prototype Implementation: Keyboard Chat Input HUD
Stored in roadmap-temp/ for reference and future integration.
"""
import flet as ft
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_chat_input")

class KeyboardChatHUD:
    """Allows users to type text commands directly to Home Assistant's Assist engine inside the transparent HUD overlay."""
    
    def __init__(self, ha_client_callback=None):
        self.client_callback = ha_client_callback
        self.chat_container = None
        self.input_field = None

    def build_chat_widget(self, page: ft.Page) -> ft.Control:
        """Construct the floating text entry field."""
        
        self.input_field = ft.TextField(
            hint_text="Ask Home Assistant...",
            hint_style=ft.TextStyle(color=ft.Colors.with_opacity(0.5, ft.Colors.WHITE)),
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            border_color=ft.Colors.with_opacity(0.3, ft.Colors.WHITE),
            focused_border_color=ft.Colors.LIGHT_BLUE_ACCENT,
            cursor_color=ft.Colors.LIGHT_BLUE_ACCENT,
            expand=True,
            on_submit=lambda e: self._submit_command(page)
        )
        
        send_btn = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.LIGHT_BLUE_ACCENT,
            on_click=lambda e: self._submit_command(page)
        )
        
        self.chat_container = ft.Container(
            content=ft.Row([
                self.input_field,
                send_btn
            ], spacing=5),
            padding=10,
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.BLACK),
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            blur=ft.Blur(10, 10, ft.BlurStyle.OUTER),
            width=450,
            visible=False,
            margin=ft.margin.only(bottom=10) # Rendered right above the Siri conic border
        )
        return self.chat_container

    def toggle_chat_hud(self, page: ft.Page):
        """Toggle the visibility of the text chat input box and focus input."""
        if not self.chat_container:
            return
            
        self.chat_container.visible = not self.chat_container.visible
        if self.chat_container.visible:
            self.input_field.focus()
            logger.info("Keyboard Chat HUD activated.")
        else:
            self.input_field.value = ""
            logger.info("Keyboard Chat HUD deactivated.")
            
        page.update()

    def _submit_command(self, page: ft.Page):
        """Sends the typed query string to Home Assistant."""
        text = self.input_field.value.strip()
        if not text:
            return
            
        logger.info(f"Submitting typed voice command: '{text}'")
        
        # Trigger Home Assistant Assist service call
        if self.client_callback:
            # Send text intent query
            self.client_callback(text)
            
        # Clear input field and close container
        self.input_field.value = ""
        self.chat_container.visible = False
        page.update()
