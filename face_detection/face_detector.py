import cv2
import face_recognition as fr  # Use alias to avoid confusion
import numpy as np
import os
import pickle
from typing import List, Tuple, Optional, Dict, Any
import time
from concurrent.futures import ThreadPoolExecutor
import threading

class FaceDetector:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        
        # Performance optimization settings
        self.scale_factor = 0.5  # Scale down images for faster processing
        self.model = "hog"  # Use HOG model for faster detection (vs "cnn")
        self.num_jitters = 5  # Number of times to re-sample for encoding
        self.tolerance = 0.5  # Face matching tolerance (lower = stricter)
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Cache for recent detections
        self.detection_cache = {}
        self.cache_timeout = 2.0  # seconds
        
    def load_known_faces(self, face_data: List[Dict[str, Any]]):
        """
        Load known faces from database with support for multiple encodings per person
        Args:
            face_data: List of dictionaries with 'id', 'name', 'employee_id', 'encodings'
        """
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        
        for face_info in face_data:
            # Support multiple encodings per person
            encodings = face_info.get('encodings', [face_info.get('encoding')])
            if not isinstance(encodings, list):
                encodings = [encodings]
            
            for encoding in encodings:
                if encoding is not None:
                    self.known_face_encodings.append(encoding)
                    self.known_face_names.append(face_info['name'])
                    self.known_face_ids.append(face_info['id'])
    
    def detect_faces_optimized(self, frame: np.ndarray, skip_frames: int = 2) -> List[Tuple]:
        """
        Optimized face detection with frame skipping and caching
        Args:
            frame: Input video frame
            skip_frames: Process every nth frame for performance
        Returns:
            List of tuples (name, location, confidence)
        """
        # Check cache first
        frame_hash = hash(frame.tobytes())
        current_time = time.time()
        
        if frame_hash in self.detection_cache:
            cache_time, cached_result = self.detection_cache[frame_hash]
            if current_time - cache_time < self.cache_timeout:
                return cached_result
        
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Fast face detection using HOG
        face_locations = fr.face_locations(rgb_small_frame, model=self.model)
        
        if not face_locations:
            result = [("No face detected", None, 0.0)]
            self.detection_cache[frame_hash] = (current_time, result)
            return result
        
        # Get face encodings
        face_encodings = fr.face_encodings(rgb_small_frame, face_locations, 
                                          num_jitters=self.num_jitters)
        
        results = []
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Scale back the face location
            top, right, bottom, left = face_location
            top = int(top / self.scale_factor)
            right = int(right / self.scale_factor)
            bottom = int(bottom / self.scale_factor)
            left = int(left / self.scale_factor)
            scaled_location = (top, right, bottom, left)
            
            if len(self.known_face_encodings) > 0:
                # Fast face matching with vectorized operations
                face_distances = fr.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                confidence = 1 - face_distances[best_match_index]
                
                if face_distances[best_match_index] <= self.tolerance:
                    name = self.known_face_names[best_match_index]
                else:
                    name = "Unknown Person"
                    confidence = 0.0
            else:
                name = "Unknown Person"
                confidence = 0.0
            
            results.append((name, scaled_location, confidence))
        
        # Cache the result
        self.detection_cache[frame_hash] = (current_time, results)
        
        # Clean old cache entries
        self._clean_cache(current_time)
        
        return results
    
    def _clean_cache(self, current_time: float):
        """Clean expired cache entries"""
        expired_keys = [k for k, (t, _) in self.detection_cache.items() 
                       if current_time - t > self.cache_timeout]
        for key in expired_keys:
            del self.detection_cache[key]
    
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
    
    def encode_multiple_faces(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """
        Encode multiple face images for better recognition accuracy
        Args:
            images: List of face images
        Returns:
            List of face encodings
        """
        encodings = []
        
        for image in images:
            try:
                # Convert BGR to RGB if needed
                if len(image.shape) == 3 and image.shape[2] == 3:
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                else:
                    rgb_image = image
                
                # Resize for faster processing
                height, width = rgb_image.shape[:2]
                if width > 800:
                    scale = 800 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    rgb_image = cv2.resize(rgb_image, (new_width, new_height))
                
                # Fast face detection
                face_locations = fr.face_locations(rgb_image, model=self.model)
                
                if len(face_locations) == 0:
                    continue
                
                # Get face encodings with optimized settings
                face_encodings = fr.face_encodings(rgb_image, face_locations, 
                                                 num_jitters=self.num_jitters)
                
                if len(face_encodings) > 0:
                    encodings.append(face_encodings[0])
                    
            except Exception as e:
                print(f"Error processing image: {e}")
                continue
        
        return encodings
    
    def average_encodings(self, encodings: List[np.ndarray]) -> np.ndarray:
        """
        Average multiple face encodings for better representation
        Args:
            encodings: List of face encodings
        Returns:
            Averaged face encoding
        """
        if not encodings:
            return None
        
        if len(encodings) == 1:
            return encodings[0]
        
        # Stack and average the encodings
        stacked_encodings = np.array(encodings)
        averaged_encoding = np.mean(stacked_encodings, axis=0)
        
        return averaged_encoding
    
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
