"""
Prototype Implementation: Real-time Transcript Overlay
Stored in roadmap-temp/ for reference and future integration.
"""
import flet as ft
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_transcript_overlay")

class TranscriptOverlayApp:
    """Manages the UI layout showing streaming transcript text in the overlay window."""
    
    def __init__(self):
        self.transcript_text = None
        self.transcript_card = None
        self.active_pipeline_text = None

    def build_overlay_widgets(self) -> ft.Control:
        """Create and configure the transcript display card."""
        
        # Text label containing the transcribing words
        self.transcript_text = ft.Text(
            "Listening...",
            size=18,
            weight=ft.FontWeight.W_400,
            color=ft.Colors.WHITE,
            italic=True,
            max_lines=3,
            overflow=ft.TextOverflow.ELLIPSIS
        )
        
        # Subtext indicating active Home Assistant pipeline state
        self.active_pipeline_text = ft.Text(
            "Home Assistant pipeline active",
            size=11,
            color=ft.Colors.with_opacity(0.6, ft.Colors.WHITE)
        )
        
        # The main card containing transcript texts, utilizing glassmorphism styles
        self.transcript_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.MIC_OUTLINED, color=ft.Colors.LIGHT_BLUE_ACCENT, size=16),
                            self.active_pipeline_text
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=5
                    ),
                    self.transcript_text
                ],
                spacing=8,
                tight=True
            ),
            padding=15,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.BLACK),
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            blur=ft.Blur(12, 12, ft.BlurStyle.OUTER), # True glassmorphism
            width=500,
            margin=ft.margin.only(bottom=50), # Offset from the conic border slightly
            visible=False # Hidden until voice activation starts
        )
        
        return self.transcript_card

    def update_transcript(self, page: ft.Page, text: str, is_final: bool = False):
        """Update the overlay text with the latest STT stream."""
        if not self.transcript_card or not self.transcript_text:
            return
            
        self.transcript_card.visible = True
        self.transcript_text.value = text
        
        if is_final:
            self.transcript_text.italic = False
            self.transcript_text.color = ft.Colors.GREEN_ACCENT
            self.active_pipeline_text.value = "Processing command..."
        else:
            self.transcript_text.italic = True
            self.transcript_text.color = ft.Colors.WHITE
            self.active_pipeline_text.value = "Transcribing..."
            
        try:
            page.update()
        except Exception:
            pass

    def reset_overlay(self, page: ft.Page):
        """Hide card and clear text when speaking completes."""
        if not self.transcript_card:
            return
            
        self.transcript_card.visible = False
        self.transcript_text.value = ""
        self.active_pipeline_text.value = ""
        
        try:
            page.update()
        except Exception:
            pass

# Mocking incoming websocket events
def on_websocket_message(overlay_app: TranscriptOverlayApp, page: ft.Page, raw_message: str):
    """Processes incoming events from the Home Assistant client pipeline."""
    try:
        data = json.loads(raw_message)
        event_type = data.get("type")
        
        if event_type == "stt_stream":
            # Real-time transcribed segment (streaming STT)
            text = data.get("text", "")
            is_final = data.get("is_final", False)
            overlay_app.update_transcript(page, text, is_final)
            
        elif event_type == "pipeline_completed":
            # Command finished processing
            overlay_app.reset_overlay(page)
            
    except Exception as e:
        logger.error(f"Error handling websocket event: {e}")
