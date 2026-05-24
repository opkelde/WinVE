"""
Home Assistant WebSocket client utility for WinVE.
Provides basic connection, authentication, service calls, and media player volume controls.
Voice pipeline logic has been completely removed in favor of ESPHome Voice Satellite mode.
"""
import json
import asyncio
import websockets
import utils

logger = utils.setup_logger()

class HomeAssistantClient:
    """Home Assistant client class for service calls and volume control."""
    
    def __init__(self, host=None, token=None):
        """Initialize Home Assistant client."""
        self.host = host or utils.get_env("HA_HOST", "localhost:8123")
        self.token = token or utils.get_env("HA_TOKEN")
        self.pipeline_id = utils.get_env("HA_PIPELINE_ID")
        self.sample_rate = utils.get_env("HA_SAMPLE_RATE", 16000, int)
        
        if not self.token:
            raise ValueError("Missing access token in .env file (HA_TOKEN)")
        
        self.websocket = None
        self.message_id = 1
        self.connected = False
        self.volumes_managed = False  # Flag to track if we're managing volumes
        self.saved_volumes_for_restore = None  # Store volumes for restoration
        self.available_pipelines = []
        
    async def connect(self):
        """Establish WebSocket connection with Home Assistant."""
        host_clean = self.host.strip()
        protocol = None
        
        # Check if protocol is specified in host string
        if host_clean.startswith("ws://"):
            protocol = "ws"
            host_clean = host_clean[5:]
        elif host_clean.startswith("wss://"):
            protocol = "wss"
            host_clean = host_clean[6:]
        elif host_clean.startswith("http://"):
            protocol = "ws"
            host_clean = host_clean[7:]
        elif host_clean.startswith("https://"):
            protocol = "wss"
            host_clean = host_clean[8:]
            
        if not protocol:
            # Fallback heuristic
            if host_clean.startswith(('localhost', '127.0.0.1', '192.168.', '10.', '172.')) or ":8123" in host_clean:
                protocol = "ws"
            else:
                protocol = "wss"
                
        uri = f"{protocol}://{host_clean}/api/websocket"
        logger.info(f"Connecting to Home Assistant: {uri}")
        
        ssl_context = None
        if protocol == "wss":
            import ssl
            verify_ssl = utils.get_env_bool("HA_VERIFY_SSL", True)
            if not verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                logger.warning("SSL verification is disabled for Home Assistant connection")
        
        try:
            connect_kwargs = {"max_size": 10 * 1024 * 1024}
            if ssl_context:
                connect_kwargs["ssl"] = ssl_context
                
            self.websocket = await asyncio.wait_for(
                websockets.connect(uri, **connect_kwargs),
                timeout=15.0
            )
            logger.info("Connection established")
            
            auth_message = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=15.0
            )
            auth_message = json.loads(auth_message)
            
            if auth_message["type"] != "auth_required":
                logger.error(f"Unexpected message: {auth_message}")
                await self.websocket.close()
                return False
            
            await self.websocket.send(json.dumps({
                "type": "auth",
                "access_token": self.token
            }))
            
            auth_result = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=15.0
            )
            auth_result = json.loads(auth_result)
            
            if auth_result["type"] != "auth_ok":
                logger.error(f"Authentication failed: {auth_result}")
                await self.websocket.close()
                return False
            
            logger.info("Authentication completed successfully")
            self.connected = True
            return True
            
        except asyncio.TimeoutError:
            logger.error("Timeout during connection to Home Assistant")
            return False
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    async def fetch_available_pipelines(self):
        """Fetch available pipelines from Home Assistant."""
        try:
            logger.info("Fetching available pipelines from Home Assistant")
            
            await self.websocket.send(json.dumps({
                "id": self.message_id,
                "type": "assist_pipeline/pipeline/list"
            }))
            current_msg_id = self.message_id
            self.message_id += 1
            
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=10.0
            )
            response_json = json.loads(response)
            
            if (response_json.get("id") == current_msg_id and 
                response_json.get("type") == "result" and 
                response_json.get("success")):
                
                self.available_pipelines = response_json.get("result", {}).get("pipelines", [])
                logger.info(f"Found {len(self.available_pipelines)} pipelines")
            else:
                logger.error(f"Failed to fetch pipelines: {response_json}")
                self.available_pipelines = []
                
        except Exception as e:
            logger.error(f"Error fetching pipelines: {e}")
            self.available_pipelines = []

    def get_available_pipelines(self):
        """Get available pipelines."""
        return self.available_pipelines

    def validate_pipeline_id(self, pipeline_id):
        """Validate pipeline ID."""
        if not self.available_pipelines:
            return False
        return any(p.get("id") == pipeline_id for p in self.available_pipelines)

    async def test_connection(self):
        """Test connection without creating pipeline."""
        try:
            if not self.connected:
                success = await self.connect()
                if not success:
                    return False, "Cannot establish connection"
            
            if not self.available_pipelines:
                await self.fetch_available_pipelines()
            
            pipeline_count = len(self.available_pipelines)
            return True, f"Connection OK. Available pipelines: {pipeline_count}"
            
        except Exception as e:
            return False, f"Test error: {str(e)}"
    
    async def close(self):
        """Close connection."""
        self.connected = False
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("Connection closed")
            except Exception as e:
                logger.error(f"Connection closing error: {e}")
            finally:
                self.websocket = None

    async def call_service(self, service_call):
        """Call a Home Assistant service."""
        try:
            if '.' not in service_call:
                logger.error(f"Invalid service call format: {service_call}")
                return False
            
            domain, service = service_call.split('.', 1)
            logger.info(f"Calling HA service: {domain}.{service}")
            
            service_message = {
                "id": self.message_id,
                "type": "call_service",
                "domain": domain,
                "service": service,
                "service_data": {}
            }
            
            await self.websocket.send(json.dumps(service_message))
            self.message_id += 1
            
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=10.0
            )
            
            result = json.loads(response)
            if result.get("success", False):
                logger.info(f"Service {service_call} executed successfully")
                return True
            else:
                logger.warning(f"Service {service_call} failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error calling service {service_call}: {e}")
            return False
    
    async def call_service_with_data(self, domain, service, service_data):
        """Call HA service with custom data."""
        try:
            logger.info(f"Calling HA service: {domain}.{service} with data: {service_data}")
            
            service_message = {
                "id": self.message_id,
                "type": "call_service",
                "domain": domain,
                "service": service,
                "service_data": service_data
            }
            
            await self.websocket.send(json.dumps(service_message))
            self.message_id += 1
            
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=10.0
            )
            
            result = json.loads(response)
            if result.get("success", True):  # Most services succeed
                logger.info(f"Service {domain}.{service} executed successfully")
                return True
            else:
                logger.warning(f"Service {domain}.{service} failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error calling service {domain}.{service}: {e}")
            return False

    async def get_media_player_entities(self):
        """Get list of all media_player entities from Home Assistant."""
        try:
            logger.info("Fetching media_player entities from Home Assistant")
            
            await self.websocket.send(json.dumps({
                "id": self.message_id,
                "type": "get_states"
            }))
            current_msg_id = self.message_id
            self.message_id += 1
            
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=15.0
            )
            response_json = json.loads(response)
            
            if (response_json.get("id") == current_msg_id and 
                response_json.get("type") == "result" and 
                response_json.get("success")):
                
                entities = response_json.get("result", [])
                media_players = []
                
                for entity in entities:
                    entity_id = entity.get("entity_id", "")
                    if entity_id.startswith("media_player."):
                        attributes = entity.get("attributes", {})
                        friendly_name = attributes.get("friendly_name", entity_id)
                        current_volume = attributes.get("volume_level")
                        
                        media_players.append({
                            "entity_id": entity_id,
                            "friendly_name": friendly_name,
                            "current_volume": current_volume
                        })
                
                logger.info(f"Found {len(media_players)} media_player entities")
                return media_players
            else:
                logger.error(f"Failed to fetch entities: {response_json}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching media_player entities: {e}")
            return []

    async def get_entity_volume(self, entity_id):
        """Get current volume level of a media_player entity."""
        try:
            await self.websocket.send(json.dumps({
                "id": self.message_id,
                "type": "get_states"
            }))
            current_msg_id = self.message_id
            self.message_id += 1
            
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=10.0
            )
            response_json = json.loads(response)
            
            if (response_json.get("id") == current_msg_id and 
                response_json.get("type") == "result" and 
                response_json.get("success")):
                
                entities = response_json.get("result", [])
                for entity in entities:
                    if entity.get("entity_id") == entity_id:
                        volume_level = entity.get("attributes", {}).get("volume_level")
                        if volume_level is not None:
                            logger.info(f"Volume for {entity_id}: {volume_level}")
                            return float(volume_level)
                        
                logger.warning(f"Volume level not found for {entity_id}")
                return None
            else:
                logger.error(f"Failed to get entity state: {response_json}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting volume for {entity_id}: {e}")
            return None

    async def set_entity_volume(self, entity_id, volume_level):
        """Set volume level for a media_player entity."""
        try:
            logger.info(f"Setting volume for {entity_id} to {volume_level}")
            
            service_data = {
                "entity_id": entity_id,
                "volume_level": float(volume_level)
            }
            
            return await self.call_service_with_data("media_player", "volume_set", service_data)
                
        except Exception as e:
            logger.error(f"Error setting volume for {entity_id}: {e}")
            return False

    async def get_multiple_volumes(self, entity_ids):
        """Get current volume levels for multiple media_player entities."""
        volumes = {}
        try:
            await self.websocket.send(json.dumps({
                "id": self.message_id,
                "type": "get_states"
            }))
            current_msg_id = self.message_id
            self.message_id += 1
            
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=10.0
            )
            response_json = json.loads(response)
            
            if (response_json.get("id") == current_msg_id and 
                response_json.get("type") == "result" and 
                response_json.get("success")):
                
                entities = response_json.get("result", [])
                for entity in entities:
                    entity_id = entity.get("entity_id")
                    if entity_id in entity_ids:
                        volume_level = entity.get("attributes", {}).get("volume_level")
                        if volume_level is not None:
                            volumes[entity_id] = float(volume_level)
                
                logger.info(f"Retrieved volumes: {volumes}")
                return volumes
            else:
                logger.error(f"Failed to get entity states: {response_json}")
                return volumes
                
        except Exception as e:
            logger.error(f"Error getting multiple volumes: {e}")
            return volumes

    async def set_multiple_volumes(self, volume_settings):
        """Set volume levels for multiple media_player entities."""
        results = {}
        for entity_id, volume_level in volume_settings.items():
            success = await self.set_entity_volume(entity_id, volume_level)
            results[entity_id] = success
        return results