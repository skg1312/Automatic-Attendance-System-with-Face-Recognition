import cv2
import face_recognition as fr  # Use alias to avoid confusion
import numpy as np
import os
import pickle
from typing import List, Tuple, Optional, Dict, Any

class FaceDetector:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        
    def load_known_faces(self, face_data: List[Dict[str, Any]]):
        """
        Load known faces from database
        Args:
            face_data: List of dictionaries with 'id', 'name', 'employee_id', 'encoding'
        """
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        
        for face_info in face_data:
            self.known_face_encodings.append(face_info['encoding'])
            self.known_face_names.append(face_info['name'])
            self.known_face_ids.append(face_info['id'])
    
    def detect_faces_in_frame(self, frame, scale_factor=0.25):
        """
        Detect and recognize faces in a frame
        Args:
            frame: Input image frame
            scale_factor: Scale factor for processing (smaller = faster)
        Returns:
            List of tuples (name, confidence, location, user_id)
        """
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find face locations and encodings
        face_locations = fr.face_locations(rgb_small_frame)
        face_encodings = fr.face_encodings(rgb_small_frame, face_locations)
        
        detected_faces = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Compare with known faces
            if len(self.known_face_encodings) > 0:
                matches = fr.compare_faces(self.known_face_encodings, face_encoding)
                face_distances = fr.face_distance(self.known_face_encodings, face_encoding)
                
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    user_id = self.known_face_ids[best_match_index]
                    confidence = 1 - face_distances[best_match_index]
                    
                    # Scale back up face location
                    scaled_location = tuple(int(coord / scale_factor) for coord in face_location)
                    
                    detected_faces.append((name, confidence, scaled_location, user_id))
        
        return detected_faces
    
    def encode_face_from_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Extract face encoding from an image file
        Args:
            image_path: Path to the image file
        Returns:
            Face encoding array or None if no face found
        """
        try:
            # Load image
            image = fr.load_image_file(image_path)
            
            # Find face locations
            face_locations = fr.face_locations(image)
            
            if len(face_locations) == 0:
                return None
            
            # Get face encodings
            face_encodings = fr.face_encodings(image, face_locations)
            
            if len(face_encodings) > 0:
                return face_encodings[0]
            
            return None
        except Exception as e:
            print(f"Error encoding face from {image_path}: {e}")
            return None
    
    def encode_face_from_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract face encoding from a frame
        Args:
            frame: Input image frame
        Returns:
            Face encoding array or None if no face found
        """
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find face locations
            face_locations = fr.face_locations(rgb_frame)
            
            if len(face_locations) == 0:
                return None
            
            # Get face encodings
            face_encodings = fr.face_encodings(rgb_frame, face_locations)
            
            if len(face_encodings) > 0:
                return face_encodings[0]
            
            return None
        except Exception as e:
            print(f"Error encoding face from frame: {e}")
            return None
    
    def draw_face_boxes(self, frame: np.ndarray, detected_faces: List[Tuple]) -> np.ndarray:
        """
        Draw bounding boxes and labels on detected faces
        Args:
            frame: Input image frame
            detected_faces: List of detected faces (name, confidence, location, user_id)
        Returns:
            Frame with drawn boxes and labels
        """
        for name, confidence, (top, right, bottom, left), user_id in detected_faces:
            # Draw rectangle around face
            color = (0, 255, 0) if confidence > 0.6 else (0, 255, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw label
            label = f"{name} ({confidence:.2f})"
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6),
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
        
        return frame
    
    def validate_face_quality(self, frame: np.ndarray) -> Tuple[bool, str]:
        """
        Validate if the face in frame is of good quality for recognition
        Args:
            frame: Input image frame
        Returns:
            (is_valid, message)
        """
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = fr.face_locations(rgb_frame)
            
            if len(face_locations) == 0:
                return False, "No face detected"
            
            if len(face_locations) > 1:
                return False, "Multiple faces detected. Please ensure only one person is visible"
            
            # Check face size
            top, right, bottom, left = face_locations[0]
            face_width = right - left
            face_height = bottom - top
            
            # Face should be at least 100x100 pixels
            if face_width < 100 or face_height < 100:
                return False, "Face too small. Please move closer to the camera"
            
            # Check if face is roughly centered
            frame_height, frame_width = frame.shape[:2]
            face_center_x = (left + right) // 2
            face_center_y = (top + bottom) // 2
            frame_center_x = frame_width // 2
            frame_center_y = frame_height // 2
            
            if abs(face_center_x - frame_center_x) > frame_width * 0.3:
                return False, "Please center your face horizontally"
            
            if abs(face_center_y - frame_center_y) > frame_height * 0.3:
                return False, "Please center your face vertically"
            
            return True, "Face quality is good"
            
        except Exception as e:
            return False, f"Error validating face: {e}"

class FaceEncoder:
    @staticmethod
    def save_encoding(encoding: np.ndarray, file_path: str):
        """Save face encoding to file"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            pickle.dump(encoding, f)
    
    @staticmethod
    def load_encoding(file_path: str) -> Optional[np.ndarray]:
        """Load face encoding from file"""
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading encoding from {file_path}: {e}")
            return None
    
    @staticmethod
    def compare_encodings(encoding1: np.ndarray, encoding2: np.ndarray, tolerance: float = 0.6) -> Tuple[bool, float]:
        """
        Compare two face encodings
        Args:
            encoding1: First face encoding
            encoding2: Second face encoding
            tolerance: Comparison tolerance (lower = stricter)
        Returns:
            (is_match, distance)
        """
        distance = fr.face_distance([encoding1], encoding2)[0]
        is_match = distance <= tolerance
        return is_match, distance
