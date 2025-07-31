"""
Face Encoding Utilities

This module provides utilities for face encoding operations,
including saving and loading face encodings from files.
"""

import numpy as np
import pickle
import os
from typing import Optional, Dict, Any
import logging

class FaceEncoder:
    """Utility class for face encoding operations"""
    
    def __init__(self, encodings_dir: str = "data/encodings"):
        """
        Initialize Face Encoder
        Args:
            encodings_dir: Directory to store face encodings
        """
        self.encodings_dir = encodings_dir
        os.makedirs(encodings_dir, exist_ok=True)
    
    def save_encoding(self, user_id: str, face_encoding: np.ndarray) -> bool:
        """
        Save face encoding to file
        Args:
            user_id: Unique identifier for the user
            face_encoding: Face encoding array
        Returns:
            bool: True if successful
        """
        try:
            filename = f"{user_id}_encoding.pkl"
            filepath = os.path.join(self.encodings_dir, filename)
            
            with open(filepath, 'wb') as f:
                pickle.dump(face_encoding, f)
            
            return True
        except Exception as e:
            logging.error(f"Error saving face encoding for {user_id}: {e}")
            return False
    
    def load_encoding(self, user_id: str) -> Optional[np.ndarray]:
        """
        Load face encoding from file
        Args:
            user_id: Unique identifier for the user
        Returns:
            Face encoding array or None if not found
        """
        try:
            filename = f"{user_id}_encoding.pkl"
            filepath = os.path.join(self.encodings_dir, filename)
            
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'rb') as f:
                face_encoding = pickle.load(f)
            
            return face_encoding
        except Exception as e:
            logging.error(f"Error loading face encoding for {user_id}: {e}")
            return None
    
    def delete_encoding(self, user_id: str) -> bool:
        """
        Delete face encoding file
        Args:
            user_id: Unique identifier for the user
        Returns:
            bool: True if successful
        """
        try:
            filename = f"{user_id}_encoding.pkl"
            filepath = os.path.join(self.encodings_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            
            return False
        except Exception as e:
            logging.error(f"Error deleting face encoding for {user_id}: {e}")
            return False
    
    def list_encodings(self) -> Dict[str, str]:
        """
        List all available face encodings
        Returns:
            Dictionary mapping user_id to file path
        """
        encodings = {}
        try:
            for filename in os.listdir(self.encodings_dir):
                if filename.endswith('_encoding.pkl'):
                    user_id = filename.replace('_encoding.pkl', '')
                    filepath = os.path.join(self.encodings_dir, filename)
                    encodings[user_id] = filepath
        except Exception as e:
            logging.error(f"Error listing face encodings: {e}")
        
        return encodings
    
    def validate_encoding(self, face_encoding: np.ndarray) -> bool:
        """
        Validate face encoding format
        Args:
            face_encoding: Face encoding to validate
        Returns:
            bool: True if valid
        """
        if not isinstance(face_encoding, np.ndarray):
            return False
        
        # face_recognition library typically produces 128-dimensional encodings
        if face_encoding.shape != (128,):
            return False
        
        return True
