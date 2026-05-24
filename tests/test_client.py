"""
Tests for client module (Home Assistant WebSocket client).
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import client


class TestHomeAssistantClient:
    """Test cases for HomeAssistantClient class."""
    
    @patch.dict('os.environ', {
        'HA_HOST': 'test-host:8123',
        'HA_TOKEN': 'test-token',
        'HA_PIPELINE_ID': 'test-pipeline',
        'HA_SAMPLE_RATE': '16000'
    })
    def test_init_success(self):
        """Test successful client initialization."""
        ha_client = client.HomeAssistantClient()
        
        assert ha_client.host == 'test-host:8123'
        assert ha_client.token == 'test-token'
        assert ha_client.pipeline_id == 'test-pipeline'
        assert ha_client.sample_rate == 16000
        assert ha_client.connected is False
        assert ha_client.message_id == 1
    
    def test_init_missing_token(self):
        """Test initialization with missing token."""
        with patch.dict('os.environ', {'HA_HOST': 'test-host'}, clear=True):
            with pytest.raises(ValueError, match="Missing access token"):
                client.HomeAssistantClient()
    
    @patch('websockets.connect')
    async def test_connect_success(self, mock_connect):
        """Test successful WebSocket connection."""
        # Mock WebSocket
        mock_ws = AsyncMock()
        async def mock_connect_coro(*args, **kwargs):
            return mock_ws
        mock_connect.side_effect = mock_connect_coro
        
        # Mock authentication flow
        mock_ws.recv.side_effect = [
            json.dumps({"type": "auth_required"}),
            json.dumps({"type": "auth_ok"})
        ]
        
        ha_client = client.HomeAssistantClient()
        ha_client.fetch_available_pipelines = AsyncMock()
        
        result = await ha_client.connect()
        
        assert result is True
        assert ha_client.connected is True
        assert ha_client.websocket == mock_ws
        
        # Verify authentication messages
        mock_ws.send.assert_called_once()
        sent_message = json.loads(mock_ws.send.call_args[0][0])
        assert sent_message["type"] == "auth"
        assert sent_message["access_token"] == ha_client.token
    
    @patch('websockets.connect')
    async def test_connect_timeout(self, mock_connect):
        """Test connection timeout."""
        mock_connect.side_effect = asyncio.TimeoutError()
        
        ha_client = client.HomeAssistantClient()
        result = await ha_client.connect()
        
        assert result is False
        assert ha_client.connected is False
    
    @patch('websockets.connect')
    async def test_connect_auth_failed(self, mock_connect):
        """Test connection with authentication failure."""
        mock_ws = AsyncMock()
        async def mock_connect_coro(*args, **kwargs):
            return mock_ws
        mock_connect.side_effect = mock_connect_coro
        
        # Mock authentication failure
        mock_ws.recv.side_effect = [
            json.dumps({"type": "auth_required"}),
            json.dumps({"type": "auth_invalid", "message": "Invalid token"})
        ]
        
        ha_client = client.HomeAssistantClient()
        result = await ha_client.connect()
        
        assert result is False
        assert ha_client.connected is False
    
    @patch('websockets.connect')
    async def test_connect_unexpected_message(self, mock_connect):
        """Test connection with unexpected initial message."""
        mock_ws = AsyncMock()
        async def mock_connect_coro(*args, **kwargs):
            return mock_ws
        mock_connect.side_effect = mock_connect_coro
        
        # Mock unexpected message
        mock_ws.recv.return_value = json.dumps({"type": "unexpected"})
        
        ha_client = client.HomeAssistantClient()
        result = await ha_client.connect()
        
        assert result is False
        assert ha_client.connected is False
    
    async def test_fetch_available_pipelines_success(self):
        """Test successful pipeline fetching."""
        ha_client = client.HomeAssistantClient()
        ha_client.websocket = AsyncMock()
        ha_client.message_id = 1
        
        # Mock pipeline response
        pipeline_response = {
            "id": 1,
            "type": "result",
            "success": True,
            "result": {
                "pipelines": [
                    {"id": "pipeline1", "name": "Pipeline 1", "language": "en"},
                    {"id": "pipeline2", "name": "Pipeline 2", "language": "pl"}
                ]
            }
        }
        
        ha_client.websocket.recv.return_value = json.dumps(pipeline_response)
        
        await ha_client.fetch_available_pipelines()
        
        assert len(ha_client.available_pipelines) == 2
        assert ha_client.available_pipelines[0]["name"] == "Pipeline 1"
        assert ha_client.available_pipelines[1]["name"] == "Pipeline 2"
        assert ha_client.message_id == 2
    
    async def test_fetch_available_pipelines_error(self):
        """Test pipeline fetching with error response."""
        ha_client = client.HomeAssistantClient()
        ha_client.websocket = AsyncMock()
        ha_client.message_id = 1
        
        # Mock error response
        error_response = {
            "id": 1,
            "type": "result",
            "success": False,
            "error": {"code": "unknown_error", "message": "Failed to fetch pipelines"}
        }
        
        ha_client.websocket.recv.return_value = json.dumps(error_response)
        
        await ha_client.fetch_available_pipelines()
        
        assert len(ha_client.available_pipelines) == 0
        assert ha_client.message_id == 2
    
    async def test_fetch_available_pipelines_timeout(self):
        """Test pipeline fetching with timeout."""
        ha_client = client.HomeAssistantClient()
        ha_client.websocket = AsyncMock()
        ha_client.websocket.recv.side_effect = asyncio.TimeoutError()
        
        await ha_client.fetch_available_pipelines()
        
        assert len(ha_client.available_pipelines) == 0
    
    def test_get_available_pipelines(self):
        """Test getting available pipelines."""
        ha_client = client.HomeAssistantClient()
        ha_client.available_pipelines = [
            {"id": "pipeline1", "name": "Pipeline 1"},
            {"id": "pipeline2", "name": "Pipeline 2"}
        ]
        
        pipelines = ha_client.get_available_pipelines()
        
        assert len(pipelines) == 2
        assert pipelines[0]["name"] == "Pipeline 1"
    
    def test_validate_pipeline_id_valid(self):
        """Test pipeline ID validation with valid ID."""
        ha_client = client.HomeAssistantClient()
        ha_client.available_pipelines = [
            {"id": "pipeline1", "name": "Pipeline 1"},
            {"id": "pipeline2", "name": "Pipeline 2"}
        ]
        
        result = ha_client.validate_pipeline_id("pipeline1")
        assert result is True
    
    def test_validate_pipeline_id_invalid(self):
        """Test pipeline ID validation with invalid ID."""
        ha_client = client.HomeAssistantClient()
        ha_client.available_pipelines = [
            {"id": "pipeline1", "name": "Pipeline 1"},
            {"id": "pipeline2", "name": "Pipeline 2"}
        ]
        
        result = ha_client.validate_pipeline_id("nonexistent")
        assert result is False
    
    def test_validate_pipeline_id_empty_list(self):
        """Test pipeline ID validation with empty pipeline list."""
        ha_client = client.HomeAssistantClient()
        ha_client.available_pipelines = []
        
        result = ha_client.validate_pipeline_id("pipeline1")
        assert result is False
    

    async def test_test_connection_success(self):
        """Test successful connection test."""
        ha_client = client.HomeAssistantClient()
        
        with patch.object(ha_client, 'connect', return_value=True), \
             patch.object(ha_client, 'close', return_value=None):
            
            success, message = await ha_client.test_connection()
            
            assert success is True
            assert "Connection OK" in message
    
    async def test_test_connection_failure(self):
        """Test connection test failure."""
        ha_client = client.HomeAssistantClient()
        
        with patch.object(ha_client, 'connect', return_value=False), \
             patch.object(ha_client, 'close', return_value=None):
            
            success, message = await ha_client.test_connection()
            
            assert success is False
            assert "Cannot establish connection" in message
    
    async def test_test_connection_exception(self):
        """Test connection test with exception."""
        ha_client = client.HomeAssistantClient()
        
        with patch.object(ha_client, 'connect', side_effect=Exception("Test error")), \
             patch.object(ha_client, 'close', return_value=None):
            
            success, message = await ha_client.test_connection()
            
            assert success is False
            assert "Test error" in message
    
    async def test_close_success(self):
        """Test successful client cleanup."""
        ha_client = client.HomeAssistantClient()
        websocket = AsyncMock()
        ha_client.websocket = websocket
        ha_client.connected = True
        
        await ha_client.close()
        
        assert ha_client.connected is False
        websocket.close.assert_called_once()
        assert ha_client.websocket is None
    
    async def test_close_no_websocket(self):
        """Test cleanup without websocket."""
        ha_client = client.HomeAssistantClient()
        ha_client.websocket = None
        ha_client.connected = True
        
        # Should not raise exception
        await ha_client.close()
        
        assert ha_client.connected is False
    
    async def test_close_with_exception(self):
        """Test cleanup with exception."""
        ha_client = client.HomeAssistantClient()
        ha_client.websocket = AsyncMock()
        ha_client.websocket.close.side_effect = Exception("Close error")
        ha_client.connected = True
        
        # Should not raise exception
        await ha_client.close()
        
        assert ha_client.connected is False
        assert ha_client.websocket is None