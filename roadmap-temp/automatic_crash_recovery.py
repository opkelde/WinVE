"""
Prototype Implementation: Automatic Crash Recovery & Watchdog
Stored in roadmap-temp/ for reference and future integration.
"""
import time
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_watchdog")

class ComponentWatchdog:
    """Monitors critical application components (WebSocket client, microphone stream, animation server) and automatically restarts them upon failure."""
    
    def __init__(self, main_app=None):
        self.main_app = main_app
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Track recovery attempts to prevent cascading loops
        self.restart_counters = {
            "websocket_client": 0,
            "audio_input": 0,
            "animation_server": 0
        }
        self.max_recovery_attempts = 5
        self.cooldown_period = 300 # Reset recovery counts after 5 minutes of stability

    def start_watchdog(self):
        """Spawns the background monitoring thread loop."""
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("WinVE system monitoring watchdog activated.")

    def _watchdog_loop(self):
        last_cooldown_reset = time.time()
        
        while self.is_monitoring:
            time.sleep(10) # Run checks every 10 seconds
            
            # Cooldown check: reset crash counts periodically
            if time.time() - last_cooldown_reset > self.cooldown_period:
                for k in self.restart_counters.keys():
                    self.restart_counters[k] = 0
                last_cooldown_reset = time.time()
                logger.debug("Watchdog recovery counters cooled down and reset.")

            if not self.main_app:
                continue

            # Check 1: WebSocket Client connection health
            self._check_websocket_health()

            # Check 2: PyAudio input stream active state
            self._check_audio_input_health()

            # Check 3: Local WebSocket server active state
            self._check_animation_server_health()

    def _check_websocket_health(self):
        """Verify client connection is active if Home Assistant coordinates are set."""
        client = getattr(self.main_app, "client", None)
        if not client:
            return
            
        is_connected = getattr(client, "is_connected", False)
        # Only recover if the main app expects to be connected
        if not is_connected and getattr(client, "ws", None) is None:
            if self.restart_counters["websocket_client"] < self.max_recovery_attempts:
                logger.warning("Watchdog Alert: Home Assistant Client is inactive. Initiating recovery...")
                self.restart_counters["websocket_client"] += 1
                
                # Run connection in background
                threading.Thread(target=client.connect, daemon=True).start()
            else:
                logger.error("Watchdog Alert: Maximum recovery attempts reached for HA Client. Requires manual restart.")

    def _check_audio_input_health(self):
        """Verify PyAudio microphone stream remains running."""
        audio_manager = getattr(self.main_app, "audio_manager", None)
        if not audio_manager:
            return
            
        stream = getattr(audio_manager, "stream", None)
        is_running = getattr(audio_manager, "is_running", False)
        
        if is_running and (stream is None or not stream.is_active()):
            if self.restart_counters["audio_input"] < self.max_recovery_attempts:
                logger.warning("Watchdog Alert: Microphone input stream went inactive. Re-initializing input pipeline...")
                self.restart_counters["audio_input"] += 1
                
                try:
                    audio_manager.close_audio()
                    audio_manager.init_audio()
                except Exception as e:
                    logger.error(f"Watchdog audio recovery attempt failed: {e}")
            else:
                logger.error("Watchdog Alert: Maximum recovery attempts reached for audio stream.")

    def _check_animation_server_health(self):
        """Verify internal WebSocket animation server remains open."""
        anim_server = getattr(self.main_app, "animation_server", None)
        if not anim_server:
            return
            
        # Skip check if it is a DummyAnimationServer
        if type(anim_server).__name__ == "DummyAnimationServer":
            return
            
        is_running = getattr(anim_server, "is_running", False)
        # If server was started but isn't marked running
        if not is_running:
            if self.restart_counters["animation_server"] < self.max_recovery_attempts:
                logger.warning("Watchdog Alert: WebSocket animation server crashed. Restarting host port...")
                self.restart_counters["animation_server"] += 1
                
                try:
                    anim_server.stop()
                    anim_server.start()
                except Exception as e:
                    logger.error(f"Watchdog animation server recovery failed: {e}")
            else:
                logger.error("Watchdog Alert: Maximum recovery attempts reached for animation server.")

    def stop_watchdog(self):
        self.is_monitoring = False
        logger.info("Watchdog monitoring stopped.")
