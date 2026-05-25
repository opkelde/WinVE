"""
Prototype Implementation: Smart Home Shortcut Dashboard
Stored in roadmap-temp/ for reference and future integration.
"""
import flet as ft
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_dashboard")

class SmartHomeDashboardWidget:
    """Provides a floating grid HUD containing favorite Home Assistant actions and widgets."""
    
    def __init__(self, client_callback=None):
        self.client_callback = client_callback
        self.dashboard_container = None

    def build_dashboard(self, page: ft.Page) -> ft.Control:
        """Construct the glassmorphic favorites dashboard."""
        
        # Grid of favorite controls
        grid = ft.GridView(
            expand=1,
            runs_count=3,
            max_extent=120,
            child_aspect_ratio=1.0,
            spacing=10,
            run_spacing=10,
        )
        
        # Add favorite cards
        grid.controls.extend([
            self._create_favorite_button("💡 Office Light", "light.office", "lightbulb_outline", page),
            self._create_favorite_button("🔌 PC Power", "switch.pc_plug", "power_settings_new", page),
            self._create_favorite_button("🚪 Garage Door", "cover.garage", "garage", page),
            self._create_favorite_button("📺 TV Toggle", "media_player.living_room_tv", "tv", page),
            self._create_favorite_button("🔒 House Lock", "lock.front_door", "lock", page),
            self._create_favorite_button("🧹 Vacuum run", "vacuum.robot", "cleaning_services", page)
        ])
        
        self.dashboard_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Text("🏡 Home Shortcuts", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.IconButton(ft.Icons.CLOSE, icon_color=ft.Colors.WHITE, on_click=lambda e: self.hide_dashboard(page))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
                    grid
                ],
                spacing=10,
                tight=True
            ),
            padding=20,
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.BLACK),
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
            blur=ft.Blur(18, 18, ft.BlurStyle.OUTER),
            width=400,
            height=300,
            visible=False,
            margin=ft.margin.only(top=50) # Floating at center-left screen space
        )
        return self.dashboard_container

    def _create_favorite_button(self, label: str, entity_id: str, icon_name: str, page: ft.Page) -> ft.Control:
        """Create a single interactive button cell in the dashboard grid."""
        
        # Convert icon string name to Icon property
        icon_prop = getattr(ft.Icons, icon_name.upper(), ft.Icons.DEVICE_UNKNOWN)
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(icon_prop, color=ft.Colors.LIGHT_BLUE_ACCENT, size=24),
                    ft.Text(label, size=11, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER, overflow=ft.TextOverflow.ELLIPSIS)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5
            ),
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
            alignment=ft.alignment.center,
            padding=10,
            on_click=lambda e: self._on_favorite_click(entity_id, page)
        )

    def _on_favorite_click(self, entity_id: str, page: ft.Page):
        logger.info(f"Dashboard button clicked: {entity_id}")
        if self.client_callback:
            # Send service call to HA
            self.client_callback(entity_id, "toggle")
            
        # Flash visual feedback
        # in implementation: trigger success state animation on HUD
        
    def show_dashboard(self, page: ft.Page):
        """Displays dashboard layout."""
        if self.dashboard_container:
            self.dashboard_container.visible = True
            page.update()
            logger.info("Dashboard HUD displayed.")

    def hide_dashboard(self, page: ft.Page):
        """Hides dashboard layout."""
        if self.dashboard_container:
            self.dashboard_container.visible = False
            page.update()
            logger.info("Dashboard HUD hidden.")
