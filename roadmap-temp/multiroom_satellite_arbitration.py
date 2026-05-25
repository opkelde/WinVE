"""
Prototype Implementation: Multi-Room Satellite Arbitration
Stored in roadmap-temp/ for reference and future integration.
"""
import socket
import json
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_arbitration")

class SatelliteArbitrationManager:
    """Manages UDP broadcast coordination to prevent multiple voice satellites from responding."""
    
    def __init__(self, port: int = 18883, device_id: str = "WinVE_Desktop"):
        self.port = port
        self.device_id = device_id
        self.is_running = False
        
        # State variables for active detection events
        self.active_detection_id = None
        self.max_received_confidence = 0.0
        self.closest_device_id = None
        self.lock = threading.Lock()
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Enable broadcasting
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Allow multiple local bindings for debug/testing
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start_listening(self):
        """Starts UDP broadcast listener thread."""
        self.is_running = True
        self.socket.bind(("", self.port))
        threading.Thread(target=self._listener_loop, daemon=True).start()
        logger.info(f"Arbitration listener active on port {self.port}")

    def _listener_loop(self):
        while self.is_running:
            try:
                data, addr = self.socket.recvfrom(2048)
                payload = json.loads(data.decode("utf-8"))
                
                if payload.get("device_id") == self.device_id:
                    continue # Ignore our own broadcasts
                    
                self._handle_arbitration_packet(payload)
            except Exception as e:
                if self.is_running:
                    logger.error(f"Error in arbitration listener: {e}")

    def _handle_arbitration_packet(self, packet: dict):
        """Evaluate incoming peer satellite wake word signals."""
        packet_type = packet.get("type")
        if packet_type != "wake_detected":
            return
            
        det_id = packet.get("detection_id") # Unique timestamp or transaction ID for the event
        confidence = float(packet.get("confidence", 0.0))
        peer_id = packet.get("device_id")

        with self.lock:
            if det_id == self.active_detection_id:
                logger.info(f"Peer '{peer_id}' detected same event with confidence {confidence:.2f}")
                if confidence > self.max_received_confidence:
                    self.max_received_confidence = confidence
                    self.closest_device_id = peer_id

    def announce_wake_word(self, detection_id: str, local_confidence: float):
        """Broadcasts wake word event details to the network."""
        logger.info(f"Wake word detected locally. Announcing: ID={detection_id}, Conf={local_confidence:.2f}")
        
        # Reset local arbitration tracking state
        with self.lock:
            self.active_detection_id = detection_id
            self.max_received_confidence = 0.0
            self.closest_device_id = self.device_id

        packet = {
            "type": "wake_detected",
            "detection_id": detection_id,
            "device_id": self.device_id,
            "confidence": local_confidence # Can represent RSSI or wake word match score
        }
        
        try:
            # Broadcast to entire subnet
            self.socket.sendto(json.dumps(packet).encode("utf-8"), ("255.255.255.255", self.port))
        except Exception as e:
            logger.error(f"Failed to broadcast arbitration packet: {e}")

    def should_i_respond(self, wait_delay_sec: float = 0.25) -> bool:
        """Wait for peer broadcasts to arrive, then decide if local satellite should speak or mute."""
        logger.info(f"Waiting {wait_delay_sec}s for arbitration network updates...")
        time.sleep(wait_delay_sec) # Short delay to gather broadcasts
        
        with self.lock:
            if self.closest_device_id == self.device_id:
                logger.info("Arbitration Won! Local satellite will handle the command.")
                return True
            else:
                logger.info(f"Arbitration Lost. Muting. Peer '{self.closest_device_id}' has stronger signal.")
                return False

    def stop(self):
        self.is_running = False
        try:
            self.socket.close()
        except:
            pass
        logger.info("Arbitration manager stopped.")
