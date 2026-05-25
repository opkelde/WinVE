"""
Prototype Implementation: Dynamic HA Pipeline Discovery & Hot-swapping
Stored in roadmap-temp/ for reference and future integration.
"""
import asyncio
import logging
import flet as ft

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_pipeline_swapper")

class PipelineHotSwapper:
    """Discovers, lists, and switches Home Assistant Assist conversation pipelines dynamically."""
    
    def __init__(self, ha_client=None):
        self.ha_client = ha_client
        self.pipelines = [] # List of dicts: [{"id": "...", "name": "...", "language": "..."}]
        self.dropdown = None
        self.current_pipeline_id = ""

    async def fetch_pipelines(self) -> list:
        """Query Home Assistant WebSocket API to discover Assist pipelines."""
        if not self.ha_client:
            # Mock pipelines if client not connected
            logger.info("HA client not connected. Returning mock pipelines...")
            self.pipelines = [
                {"id": "preferred", "name": "Preferred Pipeline", "language": "en"},
                {"id": "samantha_en", "name": "Samantha (English GPT-4)", "language": "en"},
                {"id": "jarvis_custom", "name": "Jarvis Home Automation", "language": "en"}
            ]
            return self.pipelines

        try:
            # Query Home Assistant Assist pipelines
            response = await self.ha_client.send_ws_message_with_response({
                "type": "assist_pipeline/pipeline/list"
            })
            if response and response.get("success"):
                results = response.get("result", {}).get("pipelines", [])
                self.pipelines = [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "language": p.get("language")
                    } for p in results
                ]
                logger.info(f"Discovered {len(self.pipelines)} Assist pipelines from Home Assistant.")
            return self.pipelines
        except Exception as e:
            logger.error(f"Error fetching pipelines: {e}")
            return []

    def build_selector_widget(self, page: ft.Page) -> ft.Control:
        """Create dropdown widget to change active pipeline."""
        self.dropdown = ft.Dropdown(
            label="Active Conversation Pipeline",
            hint_text="Select a pipeline",
            width=300,
            on_change=lambda e: self._on_pipeline_change(e.control.value)
        )
        
        # Populate options asynchronously
        asyncio.create_task(self._populate_options(page))
        return self.dropdown

    async def _populate_options(self, page: ft.Page):
        await self.fetch_pipelines()
        
        self.dropdown.options.clear()
        for pipe in self.pipelines:
            self.dropdown.options.append(
                ft.dropdown.Option(pipe["id"], f"{pipe['name']} ({pipe['language']})")
            )
        
        # Select active
        self.dropdown.value = self.current_pipeline_id or "preferred"
        try:
            page.update()
        except Exception:
            pass

    def _on_pipeline_change(self, pipeline_id: str):
        """Update active pipeline in settings and notify WebSocket client."""
        logger.info(f"Hot-swapping active pipeline to: {pipeline_id}")
        self.current_pipeline_id = pipeline_id
        
        # Update client connection config dynamically
        if self.ha_client:
            self.ha_client.pipeline_id = pipeline_id
            logger.info("Home Assistant Client pipeline configuration updated in-memory.")
