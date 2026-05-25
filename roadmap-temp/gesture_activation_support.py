"""
Prototype Implementation: Gesture Activation Support
Stored in roadmap-temp/ for reference and future integration.
"""
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_gesture")

class GestureActivationManager:
    """Manages optional webcam/camera tracking to activate the voice assistant based on hand gestures (like raising hand or waving)."""
    
    def __init__(self, main_app=None):
        self.main_app = main_app
        self.is_running = False
        self.thread = None
        self.camera_index = 0
        self.gesture_threshold_frames = 15 # Required consecutive frames of gesture matching to trigger

    def start_detector(self):
        """Starts webcam parser loop in background thread."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_detector, daemon=True)
        self.thread.start()
        logger.info("Gesture detection engine started.")

    def _run_detector(self):
        try:
            import cv2
            # MediaPipe is a standard library for hand gesture tracking
            import mediapipe as mp
            
            mp_hands = mp.solutions.hands
            hands = mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            
            cap = cv2.VideoCapture(self.camera_index)
            consecutive_matches = 0
            
            while self.is_running and cap.isOpened():
                success, frame = cap.read()
                if not success:
                    time.sleep(0.03)
                    continue
                
                # Flip image horizontally for natural mirroring, convert to RGB
                image = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                results = hands.process(image)
                
                gesture_matched = False
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        # Detect "raised hand" (waving) gesture:
                        # Check if finger tips are above their respective joint knobs (Y axis is inverted, 0 is top)
                        tips = [8, 12, 16, 20] # Index, middle, ring, pinky tips
                        pip_joints = [6, 10, 14, 18]
                        
                        raised_fingers = 0
                        for tip, joint in zip(tips, pip_joints):
                            if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[joint].y:
                                raised_fingers += 1
                                
                        # If 4 fingers are raised (open hand gesture)
                        if raised_fingers >= 4:
                            gesture_matched = True
                            
                if gesture_matched:
                    consecutive_matches += 1
                    if consecutive_matches >= self.gesture_threshold_frames:
                        logger.info("Webcam gesture matched: Raise Hand detected! Triggering assistant...")
                        consecutive_matches = 0 # Reset
                        
                        # Trigger voice command activation
                        if self.main_app:
                            self.main_app.trigger_voice_command()
                else:
                    # Decay matched frames count quickly
                    consecutive_matches = max(0, consecutive_matches - 2)
                    
                time.sleep(0.03) # Match target 30fps video speed
                
            cap.release()
            hands.close()
            
        except ImportError:
            logger.warning("OpenCV (cv2) or MediaPipe is not installed. Gesture activation module bypassed.")
            self.is_running = False
        except Exception as e:
            logger.error(f"Error in gesture processing thread: {e}")
            self.is_running = False

    def stop_detector(self):
        self.is_running = False
        logger.info("Gesture detection engine stopped.")
