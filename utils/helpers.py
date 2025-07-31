import os
import cv2
import numpy as np
from datetime import datetime
import streamlit as st

def ensure_directory_exists(directory_path):
    """Ensure directory exists, create if it doesn't"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        return True
    return False

def save_image(image, filename, directory="data/temp"):
    """Save image to specified directory"""
    ensure_directory_exists(directory)
    filepath = os.path.join(directory, filename)
    cv2.imwrite(filepath, image)
    return filepath

def get_timestamp_filename(prefix="img", extension=".jpg"):
    """Generate timestamp-based filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{extension}"

def resize_image(image, max_width=800, max_height=600):
    """Resize image while maintaining aspect ratio"""
    height, width = image.shape[:2]
    
    # Calculate scaling factor
    scale_w = max_width / width
    scale_h = max_height / height
    scale = min(scale_w, scale_h)
    
    # Only resize if image is larger than max dimensions
    if scale < 1:
        new_width = int(width * scale)
        new_height = int(height * scale)
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return resized
    
    return image

def validate_image_format(uploaded_file):
    """Validate uploaded image format"""
    allowed_types = ['jpg', 'jpeg', 'png', 'bmp']
    
    if uploaded_file is None:
        return False, "No file uploaded"
    
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    if file_extension not in allowed_types:
        return False, f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
    
    # Check file size (max 10MB)
    if uploaded_file.size > 10 * 1024 * 1024:
        return False, "File size too large. Maximum 10MB allowed"
    
    return True, "Valid image format"

def format_confidence(confidence):
    """Format confidence score for display"""
    if confidence is None:
        return "N/A"
    return f"{confidence:.2%}"

def format_datetime(dt_string, format_type="datetime"):
    """Format datetime string for display"""
    if not dt_string or dt_string == "None":
        return "N/A"
    
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        
        if format_type == "date":
            return dt.strftime("%Y-%m-%d")
        elif format_type == "time":
            return dt.strftime("%H:%M:%S")
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_string

def calculate_face_center(face_location):
    """Calculate center point of face bounding box"""
    top, right, bottom, left = face_location
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    return center_x, center_y

def calculate_face_size(face_location):
    """Calculate face bounding box size"""
    top, right, bottom, left = face_location
    width = right - left
    height = bottom - top
    return width, height

def is_face_centered(face_location, frame_shape, tolerance=0.3):
    """Check if face is reasonably centered in frame"""
    frame_height, frame_width = frame_shape[:2]
    face_center_x, face_center_y = calculate_face_center(face_location)
    
    frame_center_x = frame_width // 2
    frame_center_y = frame_height // 2
    
    # Calculate relative distance from center
    x_distance = abs(face_center_x - frame_center_x) / frame_width
    y_distance = abs(face_center_y - frame_center_y) / frame_height
    
    return x_distance <= tolerance and y_distance <= tolerance

def add_watermark(image, text="Face Recognition System", position="bottom-right"):
    """Add watermark to image"""
    height, width = image.shape[:2]
    
    # Set font properties
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    color = (255, 255, 255)
    thickness = 1
    
    # Get text size
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Calculate position
    if position == "bottom-right":
        x = width - text_width - 10
        y = height - 10
    elif position == "bottom-left":
        x = 10
        y = height - 10
    elif position == "top-right":
        x = width - text_width - 10
        y = text_height + 10
    else:  # top-left
        x = 10
        y = text_height + 10
    
    # Add text
    cv2.putText(image, text, (x, y), font, font_scale, color, thickness)
    return image

def create_face_grid(face_images, grid_size=(3, 3), cell_size=(150, 150)):
    """Create a grid of face images"""
    rows, cols = grid_size
    cell_width, cell_height = cell_size
    
    # Create grid image
    grid_width = cols * cell_width
    grid_height = rows * cell_height
    grid_image = np.zeros((grid_height, grid_width, 3), dtype=np.uint8)
    
    for i, face_image in enumerate(face_images[:rows * cols]):
        row = i // cols
        col = i % cols
        
        # Resize face image
        face_resized = cv2.resize(face_image, cell_size)
        
        # Calculate position in grid
        y_start = row * cell_height
        y_end = y_start + cell_height
        x_start = col * cell_width
        x_end = x_start + cell_width
        
        # Place image in grid
        grid_image[y_start:y_end, x_start:x_end] = face_resized
        
        # Add border
        cv2.rectangle(grid_image, (x_start, y_start), (x_end-1, y_end-1), (255, 255, 255), 2)
    
    return grid_image

def log_attendance_event(user_name, employee_id, action, confidence=None):
    """Log attendance events for debugging"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    confidence_str = f" (confidence: {confidence:.2f})" if confidence else ""
    
    log_message = f"[{timestamp}] {action.upper()}: {user_name} ({employee_id}){confidence_str}"
    
    # Write to log file
    log_dir = "data/logs"
    ensure_directory_exists(log_dir)
    
    log_file = os.path.join(log_dir, f"attendance_{datetime.now().strftime('%Y%m%d')}.log")
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")
    
    return log_message

def get_system_info():
    """Get system information for debugging"""
    import platform
    import sys
    
    info = {
        "Python Version": sys.version,
        "Platform": platform.platform(),
        "OpenCV Version": cv2.__version__ if 'cv2' in globals() else "Not installed",
        "Streamlit Version": st.__version__ if 'st' in globals() else "Not installed",
        "Current Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return info

def cleanup_old_files(directory, days_old=30):
    """Clean up old files from directory"""
    if not os.path.exists(directory):
        return 0
    
    cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    deleted_count = 0
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        
        if os.path.isfile(filepath):
            file_time = os.path.getmtime(filepath)
            
            if file_time < cutoff_time:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {filepath}: {e}")
    
    return deleted_count

class StreamlitUtils:
    """Utility functions for Streamlit interface"""
    
    @staticmethod
    def show_success_message(message, duration=3):
        """Show success message with auto-hide"""
        placeholder = st.empty()
        placeholder.success(message)
        # Note: Streamlit doesn't support auto-hide, but this can be extended
        return placeholder
    
    @staticmethod
    def show_loading_spinner(message="Processing..."):
        """Show loading spinner"""
        return st.spinner(message)
    
    @staticmethod
    def create_download_link(data, filename, link_text="Download"):
        """Create download link for data"""
        return st.download_button(
            label=link_text,
            data=data,
            file_name=filename,
            mime="application/octet-stream"
        )
    
    @staticmethod
    def display_metrics_row(metrics_dict):
        """Display metrics in a row"""
        cols = st.columns(len(metrics_dict))
        
        for i, (label, value) in enumerate(metrics_dict.items()):
            with cols[i]:
                st.metric(label, value)
    
    @staticmethod
    def create_info_expander(title, content_dict):
        """Create expandable info section"""
        with st.expander(title):
            for key, value in content_dict.items():
                st.write(f"**{key}:** {value}")

def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
