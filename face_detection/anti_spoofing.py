import cv2
import numpy as np
import mediapipe as mp
import time
from typing import Tuple, List, Optional

class AntiSpoofing:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Eye landmarks for blink detection (MediaPipe face mesh indices)
        # Left eye landmarks (around the eye)
        self.LEFT_EYE_LANDMARKS = [
            # Upper eyelid
            159, 145, 144, 163, 7,
            # Lower eyelid  
            33, 173, 157, 158, 154, 153, 155
        ]
        
        # Right eye landmarks (around the eye)
        self.RIGHT_EYE_LANDMARKS = [
            # Upper eyelid
            386, 374, 373, 390, 249,
            # Lower eyelid
            263, 398, 384, 385, 381, 380, 382
        ]
        
        # Simplified eye landmarks for EAR calculation
        self.LEFT_EYE_SIMPLE = [33, 160, 158, 133, 153, 144]  # left, top, bottom, right, bottom2, top2
        self.RIGHT_EYE_SIMPLE = [362, 387, 385, 263, 380, 373]  # left, top, bottom, right, bottom2, top2
        
        # Blink detection parameters
        self.EYE_AR_THRESH = 0.22  # Lowered threshold for more sensitive detection
        self.EYE_AR_CONSEC_FRAMES = 2  # Reduced frames for faster detection
        self.blink_counter = 0
        self.total_blinks = 0
        self.blink_start_time = None
        self.last_blink_time = 0
        self.eye_state = "open"  # Track eye state
        
    def calculate_eye_aspect_ratio(self, landmarks, eye_landmarks):
        """Calculate Eye Aspect Ratio (EAR) for blink detection using 6-point method"""
        try:
            # Get eye landmarks points
            points = []
            h, w = 1, 1  # Normalized coordinates
            
            for landmark_id in eye_landmarks:
                if landmark_id < len(landmarks.landmark):
                    point = landmarks.landmark[landmark_id]
                    points.append([point.x, point.y])
            
            if len(points) < 6:
                return 0.3  # Default "open" value
            
            points = np.array(points)
            
            # Calculate EAR using 6-point method
            # Points order: [left_corner, top1, top2, right_corner, bottom2, bottom1]
            # Vertical distances
            A = np.linalg.norm(points[1] - points[5])  # top1 to bottom1
            B = np.linalg.norm(points[2] - points[4])  # top2 to bottom2
            
            # Horizontal distance
            C = np.linalg.norm(points[0] - points[3])  # left to right corner
            
            # Calculate EAR
            if C == 0:
                return 0.3
            
            ear = (A + B) / (2.0 * C)
            return ear
            
        except Exception as e:
            return 0.3  # Return default "open" value on error
    
    def detect_blink(self, frame) -> Tuple[bool, int, np.ndarray]:
        """
        Detect eye blinks in the frame with improved sensitivity
        Returns: (is_blinking, total_blinks, processed_frame)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        is_blinking = False
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # Calculate EAR for both eyes using simplified landmarks
                left_ear = self.calculate_eye_aspect_ratio(face_landmarks, self.LEFT_EYE_SIMPLE)
                right_ear = self.calculate_eye_aspect_ratio(face_landmarks, self.RIGHT_EYE_SIMPLE)
                
                # Average EAR
                avg_ear = (left_ear + right_ear) / 2.0
                
                # Improved blink detection logic
                if avg_ear < self.EYE_AR_THRESH:
                    # Eye is closed
                    if self.eye_state == "open":
                        self.eye_state = "closing"
                        self.blink_counter = 1
                    else:
                        self.blink_counter += 1
                    is_blinking = True
                else:
                    # Eye is open
                    if self.eye_state == "closing" and self.blink_counter >= self.EYE_AR_CONSEC_FRAMES:
                        # Complete blink detected
                        self.total_blinks += 1
                        self.last_blink_time = time.time()
                        print(f"Blink detected! Total: {self.total_blinks}")  # Debug
                    
                    self.eye_state = "open"
                    self.blink_counter = 0
                
                # Draw eye landmarks for visualization
                self._draw_eye_landmarks(frame, face_landmarks)
                
                # Add EAR and status text
                status_color = (0, 255, 0) if avg_ear >= self.EYE_AR_THRESH else (0, 0, 255)
                cv2.putText(frame, f"EAR: {avg_ear:.3f} ({'OPEN' if avg_ear >= self.EYE_AR_THRESH else 'CLOSED'})", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        # Add blink counter
        cv2.putText(frame, f"Blinks Detected: {self.total_blinks}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        return is_blinking, self.total_blinks, frame
    
    def _draw_eye_landmarks(self, frame, face_landmarks):
        """Draw eye landmarks on frame for debugging"""
        h, w = frame.shape[:2]
        
        # Draw left eye (blue)
        for landmark_id in self.LEFT_EYE_SIMPLE:
            if landmark_id < len(face_landmarks.landmark):
                point = face_landmarks.landmark[landmark_id]
                x = int(point.x * w)
                y = int(point.y * h)
                cv2.circle(frame, (x, y), 2, (255, 0, 0), -1)
        
        # Draw right eye (green)
        for landmark_id in self.RIGHT_EYE_SIMPLE:
            if landmark_id < len(face_landmarks.landmark):
                point = face_landmarks.landmark[landmark_id]
                x = int(point.x * w)
                y = int(point.y * h)
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
    
    def is_live_person(self, blink_count: int, time_elapsed: float) -> bool:
        """
        Determine if the person is live based on blink detection
        Args:
            blink_count: Number of blinks detected
            time_elapsed: Time elapsed in seconds
        Returns:
            bool: True if person appears to be live
        """
        # More lenient requirements - require at least 1 blink in 5 seconds
        if time_elapsed >= 3:  # Check after 3 seconds minimum
            if blink_count >= 1:
                return True
        
        # Give more time if no blinks detected yet
        if time_elapsed >= 5:
            return blink_count >= 1
        
        return False
    
    def reset_blink_detection(self):
        """Reset blink detection counters"""
        self.blink_counter = 0
        self.total_blinks = 0
        self.blink_start_time = None
        self.last_blink_time = 0
        self.eye_state = "open"

class LivenessDetector:
    def __init__(self):
        self.anti_spoofing = AntiSpoofing()
        self.start_time = None
        self.detection_duration = 6  # Increased to 6 seconds for better detection
        
    def start_detection(self):
        """Start liveness detection session"""
        self.start_time = time.time()
        self.anti_spoofing.reset_blink_detection()
    
    def process_frame(self, frame) -> Tuple[bool, bool, str, np.ndarray]:
        """
        Process frame for liveness detection with improved feedback
        Returns: (is_live, detection_complete, status_message, processed_frame)
        """
        if self.start_time is None:
            self.start_detection()
        
        # Detect blinks
        is_blinking, total_blinks, processed_frame = self.anti_spoofing.detect_blink(frame)
        
        # Calculate elapsed time
        elapsed_time = time.time() - self.start_time
        remaining_time = max(0, self.detection_duration - elapsed_time)
        
        # More detailed status message
        if remaining_time > 0:
            if is_blinking:
                status_message = f"👁️ Blinking detected! Time: {remaining_time:.1f}s | Blinks: {total_blinks}"
            else:
                status_message = f"👀 Please blink naturally. Time: {remaining_time:.1f}s | Blinks: {total_blinks}"
            detection_complete = False
            
            # Early success if blink detected and some time passed
            if total_blinks >= 1 and elapsed_time >= 3:
                detection_complete = True
                is_live = True
                status_message = f"✅ Liveness verified early! Blinks: {total_blinks}"
            else:
                is_live = False
        else:
            detection_complete = True
            is_live = self.anti_spoofing.is_live_person(total_blinks, elapsed_time)
            if is_live:
                status_message = f"✅ Liveness verified! Blinks detected: {total_blinks}"
            else:
                status_message = f"❌ Liveness check failed - please blink naturally. Blinks: {total_blinks}"
        
        # Add status to frame with better visibility
        cv2.putText(processed_frame, status_message, (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        return is_live, detection_complete, status_message, processed_frame
    
    def reset(self):
        """Reset liveness detector"""
        self.start_time = None
        self.anti_spoofing.reset_blink_detection()
