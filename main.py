"""
Enhanced main.py - WinVE (Windows Voice Endpoint) main application
"""
import sys
import os

# Fix Working Directory immediately on startup (fixes startup issues from shortcuts)
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(app_dir)

# Set default background color for WebView2 to transparent to prevent white/gray flashes
import asyncio
import threading
import argparse
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item
import utils
from client import HomeAssistantClient
from audio import AudioManager
from animation_server import AnimationServer
from wake_word_detector import WakeWordDetector, validate_wake_word_config
import platform
from platform_utils import get_icon_path
from dummy_animation_server import DummyAnimationServer
from satellite_protocol import SatelliteServer

logger = utils.setup_logger()

class HAAssistApp:
    """Main application class with enhanced features."""

    def __init__(self, open_settings_on_start=False):
        """Initialize application."""
        self.audio_manager = None
        self.animation_server = None
        self.window = None
        self.settings_window = None
        self.is_running = False
        self.tray_icon = None
        self.window_visible = True
        self.wake_word_detector = None
        self.satellite_server = None
        self.connection_mode = "esphome"
        self.animations_enabled = utils.get_env_bool("HA_ANIMATIONS_ENABLED", True)
        self.response_text_enabled = utils.get_env_bool("HA_RESPONSE_TEXT_ENABLED", True)
        self.open_settings_on_start = open_settings_on_start



        # Pipeline caching
        self.cached_pipelines = []
        self.pipeline_cache_time = 0
        self._setup_wake_word_detector()

    def _setup_wake_word_detector(self):
        """Setup wake word detector with callback."""
        try:
            self.wake_word_detector = WakeWordDetector(
                callback=self.on_wake_word_detected
            )
            
            if self.wake_word_detector.enabled:
                logger.info("Wake word detector initialized and enabled")
            else:
                logger.info("Wake word detector disabled in configuration")
                
        except Exception as e:
            logger.error(f"Failed to setup wake word detector: {e}")
            self.wake_word_detector = None

    def on_wake_word_detected(self, model_name, confidence):
        """Callback when wake word is detected."""
        logger.info(f"🎯 Wake word '{model_name}' detected (confidence: {confidence:.3f})")

        if self.satellite_server:
            self.satellite_server.wakeup()
        else:
            logger.warning("Satellite server not running")

    def start_wake_word_detection(self):
        """Start wake word detection if enabled."""
        if self.wake_word_detector and self.wake_word_detector.enabled:
            success = self.wake_word_detector.start_detection()
            if success:
                logger.info("✅ Wake word detection started")
            else:
                logger.error("❌ Failed to start wake word detection")
            return success
        return False
    
    def stop_wake_word_detection(self):
        """Stop wake word detection."""
        if self.wake_word_detector:
            self.wake_word_detector.stop_detection()
            logger.info("Wake word detection stopped")

    def create_tray_icon(self):
        """Create system tray icon with cross-platform support."""
        icon_path = get_icon_path()
        
        if icon_path and os.path.exists(icon_path):
            try:
                from PIL import Image
                image = Image.open(icon_path)
                logger.info(f"Loaded tray icon: {icon_path}")
            except Exception as e:
                logger.error(f"Error loading icon: {e}")
                image = self._create_fallback_icon()
        else:
            logger.warning(f"Icon file not found, using fallback")
            image = self._create_fallback_icon()
        
        menu = self._build_tray_menu()
        
        self.tray_icon = pystray.Icon(
            "WinVE",
            image,
            "WinVE Desktop",
            menu
        )
        
        logger.info("System tray icon created")

    def _show_wake_word_status(self, icon=None, item=None):
        """Show wake word detection status with animation."""
        if not self.wake_word_detector:
            print("❌ Wake word detector not initialized")
            if self.animation_server:
                self.animation_server.show_error("Wake word detector not initialized", duration=4.0)
            return
        
        info = self.wake_word_detector.get_model_info()
        
        status_lines = []
        status_lines.append(f"Enabled: {'✅ Yes' if info['enabled'] else '❌ No'}")
        status_lines.append(f"Running: {'✅ Yes' if info['is_running'] else '❌ No'}")
        status_lines.append(f"Models: {', '.join(info['selected_models'])}")
        status_lines.append(f"Threshold: {info['detection_threshold']}")
        
        print("\n=== WAKE WORD STATUS ===")
        for line in status_lines:
            print(line)
        print(f"VAD threshold: {info['vad_threshold']}")
        print(f"Noise suppression: {'✅ Yes' if info['noise_suppression'] else '❌ No'}")
        print(f"Available models: {len(info['available_models'])}")
        print("========================\n")
        
        if info['enabled'] and info['is_running']:
            animation_message = f"Wake word: ON | Models: {', '.join(info['selected_models'])}"
            
            if self.animation_server:
                self.animation_server.show_success(animation_message, duration=5.0)
            
            print("💡 Say your wake word to test detection!")
            
        elif info['enabled'] and not info['is_running']:
            animation_message = "Wake word enabled but not running"
            
            if self.animation_server:
                self.animation_server.show_error(animation_message, duration=5.0)
            
            print("⚠️ Wake word detection enabled but not running")
            
        else:
            animation_message = "Wake word detection disabled"
            
            if self.animation_server:
                self.animation_server.show_error(animation_message, duration=4.0)
            
            print("💡 Enable wake word detection in Settings > Models")

    def _restart_wake_word(self, icon=None, item=None):
        """Restart wake word detection."""
        if not self.wake_word_detector:
            print("❌ Wake word detector not available")
            return
        
        print("🔄 Restarting wake word detection...")
        
        # Stop current detection
        self.stop_wake_word_detection()
        
        # Reload configuration and restart
        success = self.wake_word_detector.reload_models()
        
        if success:
            print("✅ Wake word detection restarted successfully")

            if self.animation_server:
                self.animation_server.show_success("Wake word restarted", duration=3.0)
        else:
            print("❌ Failed to restart wake word detection")

            if self.animation_server:
                self.animation_server.show_error("Wake word restart failed", duration=5.0)

        self._refresh_tray_menu()

    def _get_toggle_label(self):
        """Return label for pause/resume menu item."""
        if self.wake_word_detector and self.wake_word_detector.is_running:
            return '⏸ Pause wake word'
        return '▶️ Resume wake word'

    def _build_tray_menu(self):
        """Construct tray menu reflecting current state."""
        return pystray.Menu(
            item('🎤 Activate voice (%s)' % utils.get_env("HA_HOTKEY", "ctrl+shift+h"),
                 self.trigger_voice_command),
            pystray.Menu.SEPARATOR,
            item(self._get_toggle_label(), self._toggle_wake_word_detection),
            item('🎯 Wake word status', self._show_wake_word_status),
            item('🔄 Restart wake word', self._restart_wake_word),
            pystray.Menu.SEPARATOR,
            item('⚙️ Settings', self.open_settings),
            item('🔄 Test connection', self._quick_connection_test),
            pystray.Menu.SEPARATOR,
            item('❌ Close', self.quit_application)
        )

    def _refresh_tray_menu(self):
        """Update tray menu to reflect current wake word state."""
        if not self.tray_icon:
            return
        self.tray_icon.menu = self._build_tray_menu()
        try:
            self.tray_icon.update_menu()
        except Exception:
            pass

    def _toggle_wake_word_detection(self, icon=None, item=None):
        """Pause or resume wake word detection from tray."""
        if not self.wake_word_detector or not self.wake_word_detector.enabled:
            print("❌ Wake word detection not available")
            if self.animation_server:
                self.animation_server.show_error("Wake word disabled in settings", duration=3.0)
            return

        if self.wake_word_detector.is_running:
            self.stop_wake_word_detection()
            print("⏸️ Wake word detection paused")
            if self.animation_server:
                self.animation_server.show_error("Wake word paused", duration=3.0)
        else:
            started = self.start_wake_word_detection()
            if started:
                print("▶️ Wake word detection resumed")
                if self.animation_server:
                    self.animation_server.show_success("Wake word resumed", duration=3.0)
        self._refresh_tray_menu()

    def _create_fallback_icon(self):
        """Create fallback icon."""
        image = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(image)
        draw.ellipse([8, 8, 56, 56], fill='#4fc3f7', outline='white', width=2)
        draw.ellipse([24, 24, 40, 40], fill='white')
        return image
    
    def _quick_connection_test(self, icon=None, item=None):
        """Quick connection test from tray with animation."""
        def test_thread():
            try:
                test_client = HomeAssistantClient()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    success, message = loop.run_until_complete(test_client.test_connection())
                    
                    if success:
                        logger.info(f"Connection test: ✅ {message}")
                        print(f"✅ Connection test: {message}")
                        
                        if self.animation_server:
                            self.animation_server.show_success("Connection successful", duration=3.0)
                    else:
                        logger.error(f"Connection test: ❌ {message}")
                        print(f"❌ Connection test: {message}")
                        
                        if self.animation_server:
                            self.animation_server.show_error(f"Connection failed: {message}", duration=5.0)
                    
                finally:
                    loop.close()
                    
            except Exception as e:
                error_msg = f"Test error: {str(e)}"
                logger.error(error_msg)
                print(f"❌ {error_msg}")

                if self.animation_server:
                    self.animation_server.show_error(error_msg, duration=5.0)
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def _show_pipelines_info(self, icon=None, item=None):
        """Show available pipelines information."""
        def pipelines_thread():
            try:
                test_client = HomeAssistantClient()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    success = loop.run_until_complete(test_client.connect())
                    
                    if success:
                        pipelines = test_client.get_available_pipelines()
                        current_pipeline = utils.get_env("HA_PIPELINE_ID", "(default)")
                        
                        print(f"\n=== AVAILABLE PIPELINES ({len(pipelines)}) ===")
                        print(f"Currently used: {current_pipeline}")
                        print("-" * 50)
                        
                        if not pipelines:
                            print("No available pipelines or connection error")
                        else:
                            for i, pipeline in enumerate(pipelines, 1):
                                if isinstance(pipeline, str):
                                    name = pipeline
                                    pipeline_id = pipeline
                                    language = "unknown"
                                elif isinstance(pipeline, dict):
                                    name = pipeline.get("name", "Unnamed")
                                    pipeline_id = pipeline.get("id", "")
                                    language = pipeline.get("language", "unknown")
                                else:
                                    name = str(pipeline)
                                    pipeline_id = str(pipeline)
                                    language = "unknown"
                                
                                current_marker = " ← CURRENT" if pipeline_id == current_pipeline else ""
                                
                                print(f"{i}. {name}")
                                print(f"   ID: {pipeline_id}{current_marker}")
                                if language != "unknown":
                                    print(f"   Language: {language}")
                                print()
                            
                            print("=" * 50)
                            print("Use 'Settings' to change pipeline.")
                            
                            if len(pipelines) > 1:
                                print("\n💡 TIP:")
                                print("Copy the ID of chosen pipeline and paste it in app settings.")
                                
                    else:
                        print("❌ Cannot connect to Home Assistant")
                        print("Check connection settings.")
                    
                finally:
                    loop.close()
                    
            except Exception as e:
                error_msg = f"Error fetching pipelines: {str(e)}"
                logger.error(error_msg)
                print(f"❌ {error_msg}")

                print(f"📋 DEBUG: Error type: {type(e).__name__}")
                if hasattr(e, '__traceback__'):
                    import traceback
                    print("📋 Stack trace:")
                    traceback.print_exc()
        
        threading.Thread(target=pipelines_thread, daemon=True).start()

    def on_animation_state_change(self, state):
        """Handle transition state changes of the animation server."""
        logger.info(f"Animation state changed to: {state}")
        # Flet overlay handles its own visibility via WebSocket messages
        # from AnimationServer. No window manipulation needed here.

    def setup_animation_server(self):
        """Setup animation server or dummy server based on configuration."""
        if self.animations_enabled:
            from animation_server import AnimationServer
            self.animation_server = AnimationServer(state_change_callback=self.on_animation_state_change)
            logger.info("Real animation server created")
        else:
            self.animation_server = DummyAnimationServer(state_change_callback=self.on_animation_state_change)
            logger.info("Dummy animation server created (animations disabled)")
        
        self.animation_server.set_voice_command_callback(self.on_voice_command_trigger)
        self.animation_server.start()
    
    def open_settings(self, icon=None, item=None):
        """Open enhanced settings window in a separate process."""
        logger.info("Opening enhanced settings in a separate process...")
        try:
            import subprocess
            import sys
            
            if getattr(sys, 'frozen', False):
                # Compiled executable
                exe_path = sys.executable
                subprocess.Popen([exe_path, "--settings-only"])
            else:
                # Source mode
                main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                subprocess.Popen([sys.executable, main_path, "--settings-only"])
            logger.info("Settings process launched.")
        except Exception as e:
            logger.exception(f"Error opening settings: {e}")
            
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()
            
            messagebox.showerror(
                "Settings Error", 
                f"Error occurred while opening settings:\n\n{str(e)}\n\n"
                "Check application logs for details."
            )
            root.destroy()

    def on_voice_command_trigger(self):
        """Callback called when user activates voice command."""
        if self.satellite_server:
            self.satellite_server.start_conversation()
        else:
            logger.warning("ESPHome mode: satellite server not running")
    
    def hide_from_taskbar(self):
        """No-op — Flet overlay uses skip_task_bar natively."""
        pass

    def trigger_voice_command(self, icon=None, item=None):
        """Trigger from tray menu."""
        logger.info("Voice command activation from tray menu")
        self.on_voice_command_trigger()
    
    def setup_hotkey(self):
        """Setup keyboard shortcut."""
        try:
            import keyboard
            
            hotkey = utils.get_env("HA_HOTKEY", "ctrl+shift+h")
            keyboard.add_hotkey(hotkey, self.on_voice_command_trigger)
            logger.info(f"Keyboard shortcut set: {hotkey}")
            
            # Add escape key to hide interface quickly
            keyboard.add_hotkey("escape", self.hide_interface)
            logger.info("ESC key set to hide interface")
            
            return True
            
        except ImportError:
            logger.warning("keyboard library not installed - run: pip install keyboard")
            return False
        except Exception as e:
            logger.error(f"Error setting up keyboard shortcut: {e}")
            return False
    
    def hide_interface(self):
        """Hide interface immediately via ESC key."""
        if self.animation_server and self.animation_server.current_state != "hidden":
            logger.info("Hiding interface via ESC key")
            self.animation_server.change_state("hidden")
    
    def toggle_window(self, icon=None, item=None):
        """Toggle window visibility — overlay manages itself."""
        logger.info("Toggle window (overlay self-managed)")
    
    def quit_application(self, icon=None, item=None):
        """Close application from tray menu with proper cleanup."""
        logger.info("Closing application from tray menu...")
        
        # First cleanup resources
        self.cleanup()
        
        # Stop tray icon
        if self.tray_icon:
            try:
                self.tray_icon.stop()
                logger.info("Tray icon stopped")
            except Exception as e:
                logger.error(f"Error stopping tray icon: {e}")
        
        # Flet overlay cleans up automatically (daemon thread)
        
        # Give some time for cleanup to complete
        import time
        time.sleep(0.5)
        
        logger.info("Application shutdown complete")
        
        # Exit cleanly
        os._exit(0)  # Force exit without calling atexit handlers
    
    def run_tray(self):
        """Run tray icon in separate thread."""
        def tray_thread():
            try:
                self.tray_icon.run()
            except Exception as e:
                logger.exception(f"Tray icon error: {e}")
        
        threading.Thread(target=tray_thread, daemon=True).start()
        logger.info("System tray started")
    
    def _start_esphome_mode(self):
        """Start ESPHome satellite server and continuous audio streaming loop."""
        device_name = utils.get_env("DEVICE_NAME", "WinVE")
        port = utils.get_env("ESPHOME_PORT", 6053, int)
        pipeline_id = utils.get_env("HA_PIPELINE_ID")

        def on_tts_url(url: str, done_callback=None):
            """Play TTS audio from URL, call done_callback when finished."""
            host = utils.get_env("HA_HOST", "")
            threading.Thread(
                target=utils.play_audio_from_url,
                args=(url, host, None),
                kwargs={"done_callback": done_callback},
                daemon=True,
            ).start()

        def on_tts_finished():
            logger.info("TTS playback finished")

        self.satellite_server = SatelliteServer(
            device_name=device_name,
            animation_server=self.animation_server,
            on_tts_url=on_tts_url,
            on_tts_finished=on_tts_finished,
            port=port,
            pipeline_id=pipeline_id,
        )

        self.animation_server.show_connecting("Connecting...")

        async def _run_server():
            await self.satellite_server.start()
            logger.info(f"ESPHome satellite server started on port {port}")
            # Keep server running
            while self.is_running:
                await asyncio.sleep(1)
            await self.satellite_server.stop()

        def _server_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run_server())

        threading.Thread(target=_server_thread, daemon=True, name="esphome-server").start()

        # Continuous audio streaming thread - feeds mic audio to satellite server
        def _audio_stream_thread():
            import time
            logger.info("ESPHome audio stream thread started")
            while self.is_running:
                if not self.audio_manager or not self.audio_manager.stream:
                    time.sleep(0.1)
                    continue
                try:
                    data = self.audio_manager.stream.read(
                        self.audio_manager.chunk_size, exception_on_overflow=False
                    )
                    if self.satellite_server:
                        self.satellite_server.handle_audio(data)
                except Exception as e:
                    logger.debug(f"Audio stream read error: {e}")
                    time.sleep(0.05)

        threading.Thread(target=_audio_stream_thread, daemon=True, name="esphome-audio").start()
        logger.info(f"ESPHome mode active - device '{device_name}', port {port}")

    def run(self):
        """Main run method."""
        try:
            logger.info("Starting WinVE Desktop...")
            self.is_running = True

            # Initialize audio manager at startup (both modes need it)
            logger.info("Initializing audio manager...")
            try:
                self.audio_manager = AudioManager()
                self.audio_manager.init_audio()
                logger.info("✅ Audio manager initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize audio manager: {e}")
                self.audio_manager = None

            logger.info("Connection mode: ESPHome satellite")
            self.setup_animation_server()

            # Start ESPHome satellite server after animation server is ready
            if self.audio_manager:
                self._start_esphome_mode()

            self.setup_hotkey()
            self.create_tray_icon()
            self.run_tray()
            self.start_wake_word_detection()
            self._refresh_tray_menu()

            logger.info("Starting interface...")

            # Open settings automatically if --settings flag was passed
            if self.open_settings_on_start:
                def delayed_settings():
                    import time
                    time.sleep(3)
                    self.open_settings()
                threading.Thread(target=delayed_settings, daemon=True).start()

            if self.animations_enabled:
                # Launch Flet overlay (blocks main thread)
                from flet_overlay import run_overlay
                animation_port = utils.get_env("ANIMATION_PORT", 8765, int)
                logger.info(f"Starting Flet overlay on animation port {animation_port}")
                run_overlay(port=animation_port)
            else:
                logger.info("Running in headless mode (animations disabled)")
                try:
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Application interrupted by user")
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.exception(f"Application error: {str(e)}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources properly."""
        # Prevent duplicate cleanup
        if hasattr(self, '_cleanup_done') and self._cleanup_done:
            logger.debug("Cleanup already performed, skipping")
            return
            
        logger.info("Cleaning up resources...")
        self._cleanup_done = True
        self.is_running = False

        # Close settings window if open
        if self.settings_window:
            try:
                closed = False
                try:
                    closed = self.settings_window.close(timeout=2.0)
                except TypeError:
                    # Backward compatibility for legacy close() signatures.
                    self.settings_window.close()
                    closed = True

                if closed:
                    logger.info("Settings window closed")
                else:
                    logger.warning("Settings window close request timed out")
            except Exception as e:
                logger.debug(f"Error closing settings window: {e}")
            self.settings_window = None
        # Stop wake word detection first
        self.stop_wake_word_detection()

        # Stop ESPHome satellite server
        if self.satellite_server:
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.satellite_server.stop())
                loop.close()
                logger.info("ESPHome satellite server stopped")
            except Exception as e:
                logger.error(f"Error stopping satellite server: {e}")
        


        # Stop animation server
        if self.animation_server:
            try:
                self.animation_server.stop()
                logger.info("Animation server stopped")
            except Exception as e:
                logger.error(f"Error stopping animation server: {e}")
        
        # Stop background flet processes
        try:
            import subprocess
            import sys
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/IM", "flet.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Flet client processes terminated")
        except Exception as e:
            logger.debug(f"Error terminating flet processes: {e}")
        
        # Close audio manager
        if self.audio_manager:
            try:
                self.audio_manager.close_audio()
                logger.info("Audio manager closed")
            except Exception as e:
                logger.error(f"Error closing audio manager: {e}")
                
        # Cancel any remaining asyncio tasks
        try:
            # Check if there's a running event loop
            try:
                loop = asyncio.get_running_loop()
                loop_exists = True
            except RuntimeError:
                # No running loop, try to get the current one
                try:
                    loop = asyncio.get_event_loop()
                    loop_exists = not loop.is_closed()
                except RuntimeError:
                    loop_exists = False
                    loop = None
            
            if loop_exists and loop:
                pending = asyncio.all_tasks(loop)
                if pending:
                    logger.info(f"Cancelling {len(pending)} pending tasks...")
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    
                    # Give tasks a moment to cancel gracefully
                    if not loop.is_running():
                        try:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception as e:
                            logger.error(f"Error waiting for task cancellation: {e}")
            else:
                logger.debug("No active event loop found - skipping task cancellation")
                            
        except Exception as e:
            logger.error(f"Error cancelling asyncio tasks: {e}")
            
        logger.info("Cleanup completed")


def validate_configuration():
    """Validate application configuration and return list of issues."""
    issues = []

    host = utils.get_env("HA_HOST")
    token = utils.get_env("HA_TOKEN")

    if not host:
        issues.append("Missing Home Assistant server address (HA_HOST) - required for TTS playback and volume ducking")

    if not token:
        issues.append("Missing Home Assistant access token (HA_TOKEN) - required for volume ducking")
    
    sample_rate = utils.get_env("HA_SAMPLE_RATE", 16000, int)
    if sample_rate not in [8000, 16000, 22050, 44100, 48000]:
        issues.append(f"Unusual sample rate: {sample_rate}Hz")
    
    frame_duration = utils.get_env("HA_FRAME_DURATION_MS", 30, int)
    if frame_duration not in [10, 20, 30]:
        issues.append(f"Invalid VAD frame duration: {frame_duration}ms (allowed: 10, 20, 30)")
    
    vad_mode = utils.get_env("HA_VAD_MODE", 3, int)
    if vad_mode < 0 or vad_mode > 3:
        issues.append(f"Invalid VAD mode: {vad_mode} (allowed: 0-3)")

    sound_feedback = utils.get_env('HA_SOUND_FEEDBACK', 'false')
    if sound_feedback.lower() in ('true', '1', 'yes', 'y', 't'):
        sound_dir = os.path.join(os.path.dirname(__file__), 'sound')
        activation_sound = os.path.join(sound_dir, 'activation.wav')
        deactivation_sound = os.path.join(sound_dir, 'deactivation.wav')
        
        if not os.path.exists(activation_sound):
            issues.append(f"Missing activation sound file: {activation_sound}")
        
        if not os.path.exists(deactivation_sound):
            issues.append(f"Missing deactivation sound file: {deactivation_sound}")

    try:
        anim_port = utils.get_env("ANIMATION_PORT", 8765, int)
        if anim_port < 1024 or anim_port > 65535:
            issues.append(f"Invalid animation port: {anim_port} (allowed: 1024-65535)")
    except (ValueError, TypeError):
        issues.append("Animation port must be a number")
    wake_word_issues = validate_wake_word_config()
    issues.extend(wake_word_issues)
    return issues


def main():
    """Main application function with configuration validation."""
    import sys

    # Set UTF-8 encoding for console output on Windows
    if sys.platform == "win32":
        try:
            import locale
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            # Fallback for older Python versions
            os.environ["PYTHONIOENCODING"] = "utf-8"

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='WinVE - Windows Voice Endpoint for Home Assistant')
    parser.add_argument('--settings', action='store_true',
                        help='Open settings window automatically after starting the application')
    parser.add_argument('--settings-only', action='store_true',
                        help='Launch only the settings window and exit')
    args = parser.parse_args()

    if args.settings_only:
        import flet as ft
        from flet_settings import FletSettingsApp
        app = FletSettingsApp()
        ft.app(target=app.main)
        sys.exit(0)

    print("=== WinVE DESKTOP ===")
    print("Starting application...")
    print("Pre-initializing audio system...")
    try:
        import pyaudio
        temp_audio = pyaudio.PyAudio()
        temp_audio.terminate()
        print("Audio system ready")
    except Exception as e:
        print(f"Audio initialization warning: {e}")
    env_path = utils.get_env_path()
    env_found = False
    if os.path.exists(env_path):
        abs_path = os.path.abspath(env_path)
        print(f"📄 USING .ENV FILE: {abs_path}")
        env_found = True
        
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        filtered_lines = []
        for line in lines:
            if line.startswith('HA_TOKEN=') and len(line) > 20:
                filtered_lines.append(f"HA_TOKEN=***HIDDEN*** (length: {len(line.split('=', 1)[1])} chars)")
            else:
                filtered_lines.append(line)
        
        print(".ENV FILE CONTENTS:")
        print('\n'.join(filtered_lines))
        print("-" * 50)
    
    if not env_found:
        print("⚠️  NO .ENV FILE - using default settings")
        print("Run application and go to 'Settings' to configure connection.")
        print("-" * 50)
    
    print("🔍 CHECKING CONFIGURATION...")
    config_issues = validate_configuration()
    
    if config_issues:
        print("⚠️  CONFIGURATION ISSUES FOUND:")
        for issue in config_issues:
            print(f"   • {issue}")
        print("\nApplication may not work correctly.")
        print("Go to 'Settings' to fix issues.")
    else:
        print("✅ Configuration looks correct")
    
    print("-" * 50)
    
    print("📋 KEY SETTINGS:")
    important_settings = {
        'HA_HOST': utils.get_env('HA_HOST', 'MISSING'),
        'HA_PIPELINE_ID': utils.get_env('HA_PIPELINE_ID', '(default)'),
        'HA_HOTKEY': utils.get_env('HA_HOTKEY', 'ctrl+shift+h'),
        'HA_VAD_MODE': utils.get_env('HA_VAD_MODE', '3'),
        'HA_SOUND_FEEDBACK': utils.get_env('HA_SOUND_FEEDBACK', 'false'),
        'HA_WAKE_WORD_ENABLED': utils.get_env('HA_WAKE_WORD_ENABLED', 'true'),
        'DEBUG': utils.get_env('DEBUG', 'false')
    }
    
    for key, value in important_settings.items():
        print(f"   {key} = {value}")

    wake_word_enabled_str = utils.get_env('HA_WAKE_WORD_ENABLED', 'true')
    if isinstance(wake_word_enabled_str, str):
        wake_word_enabled = wake_word_enabled_str.lower() in ('true', '1', 'yes', 'y', 't')
    else:
        wake_word_enabled = bool(wake_word_enabled_str)

    if wake_word_enabled:
        models = utils.get_env('HA_WAKE_WORD_MODELS', 'computer_v2')
        print(f"   HA_WAKE_WORD_MODELS = {models}")
        print(f"   HA_WAKE_WORD_THRESHOLD = {utils.get_env('HA_WAKE_WORD_THRESHOLD', '0.5')}")
        
    token_length = len(utils.get_env('HA_TOKEN', ''))
    if token_length > 0:
        print(f"   HA_TOKEN = ***HIDDEN*** ({token_length} chars)")
    else:
        print(f"   HA_TOKEN = MISSING")
    
    print("=" * 50)

    app = HAAssistApp(open_settings_on_start=args.settings)
    app.run()
    os._exit(0)


if __name__ == "__main__":
    main()

