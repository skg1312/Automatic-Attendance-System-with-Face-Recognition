"""
Performance Configuration for Face Recognition System
This file contains all the performance optimization settings
"""

# Face Detection Performance Settings
FACE_DETECTION_CONFIG = {
    # Frame processing optimization
    'frame_scale_factor': 0.5,  # Scale down frames for faster processing
    'skip_frames': 3,  # Process every 3rd frame
    'cache_timeout': 2.0,  # Cache results for 2 seconds
    
    # Face detection model settings
    'hog_upsamples': 0,  # Reduce upsampling for faster detection
    'cnn_batch_size': 1,  # Batch size for CNN detection
    'detection_confidence_threshold': 0.5,  # Minimum confidence for face detection
    
    # Recognition settings
    'recognition_tolerance': 0.6,  # Face matching tolerance (lower = stricter)
    'max_encodings_per_user': 5,  # Maximum face encodings per user
    'unknown_person_threshold': 0.7,  # Threshold for unknown person detection
}

# Anti-Spoofing Performance Settings
LIVENESS_CONFIG = {
    'enable_by_default': True,
    'detection_frames': 10,  # Number of frames for liveness detection
    'blink_detection': True,
    'motion_detection': True,
    'texture_analysis': True,
    'confidence_threshold': 0.7,
}

# Database Performance Settings
DATABASE_CONFIG = {
    'connection_pool_size': 5,
    'query_timeout': 30,  # seconds
    'batch_insert_size': 100,
    'cache_user_encodings': True,
    'cache_timeout': 300,  # 5 minutes
}

# WebRTC Stream Settings
WEBRTC_CONFIG = {
    'video_constraints': {
        'width': 640,
        'height': 480,
        'frameRate': 15,  # Reduced frame rate for better performance
    },
    'ice_servers': [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
    ],
    'enable_audio': False,
    'async_processing': True,
}

# Multi-Image Registration Settings
REGISTRATION_CONFIG = {
    'images_per_user': 5,
    'capture_interval': 2.0,  # seconds between captures
    'image_quality_threshold': 0.6,
    'max_registration_time': 60,  # seconds
    'auto_capture': True,
    'image_preprocessing': {
        'resize_to': (150, 150),
        'face_padding': 20,
        'normalize': True,
        'enhance_contrast': False,
    }
}

# Memory Management
MEMORY_CONFIG = {
    'max_cached_frames': 10,
    'cleanup_interval': 30,  # seconds
    'gc_threshold': 100,  # MB
    'enable_memory_monitoring': False,
}

# Performance Monitoring
MONITORING_CONFIG = {
    'enable_performance_logging': False,
    'log_processing_times': False,
    'log_memory_usage': False,
    'benchmark_mode': False,
}

# Production vs Development Settings
def get_production_config():
    """Get optimized settings for production"""
    config = {
        'face_detection': FACE_DETECTION_CONFIG.copy(),
        'liveness': LIVENESS_CONFIG.copy(),
        'database': DATABASE_CONFIG.copy(),
        'webrtc': WEBRTC_CONFIG.copy(),
        'registration': REGISTRATION_CONFIG.copy(),
        'memory': MEMORY_CONFIG.copy(),
        'monitoring': MONITORING_CONFIG.copy(),
    }
    
    # Production optimizations
    config['face_detection']['frame_scale_factor'] = 0.3
    config['face_detection']['skip_frames'] = 5
    config['webrtc']['video_constraints']['frameRate'] = 10
    config['registration']['images_per_user'] = 3
    config['memory']['enable_memory_monitoring'] = True
    
    return config

def get_development_config():
    """Get settings optimized for development/testing"""
    config = {
        'face_detection': FACE_DETECTION_CONFIG.copy(),
        'liveness': LIVENESS_CONFIG.copy(),
        'database': DATABASE_CONFIG.copy(),
        'webrtc': WEBRTC_CONFIG.copy(),
        'registration': REGISTRATION_CONFIG.copy(),
        'memory': MEMORY_CONFIG.copy(),
        'monitoring': MONITORING_CONFIG.copy(),
    }
    
    # Development optimizations (prioritize quality over speed)
    config['face_detection']['frame_scale_factor'] = 0.7
    config['face_detection']['skip_frames'] = 2
    config['monitoring']['enable_performance_logging'] = True
    config['monitoring']['log_processing_times'] = True
    
    return config

# Default configuration (balanced)
DEFAULT_CONFIG = {
    'face_detection': FACE_DETECTION_CONFIG,
    'liveness': LIVENESS_CONFIG,
    'database': DATABASE_CONFIG,
    'webrtc': WEBRTC_CONFIG,
    'registration': REGISTRATION_CONFIG,
    'memory': MEMORY_CONFIG,
    'monitoring': MONITORING_CONFIG,
}
