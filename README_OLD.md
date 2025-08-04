# Automatic Attendance System with Face Recognition

An intelligent attendance system that uses facial recognition technology with anti-spoofing features including eye blink detection.

## System Features

### 🔐 Security & Authentication
- **Admin Login System** - Secure authentication with default credentials
- **Anti-spoofing Protection** - Advanced eye blink detection using MediaPipe
- **Liveness Verification** - Real-time validation to prevent photo/video attacks
- **Face Quality Validation** - Automatic face centering and quality assessment

### 👥 User Registration
- **Dual Registration Modes**: 
  - **Live Camera Registration** - Real-time WebRTC video with anti-spoofing
  - **Photo Upload Registration** - Upload existing photos for batch processing
- **Real-time Validation** - Instant feedback during registration process
- **Face Encoding Storage** - Secure storage of biometric templates

### � Attendance Management
- **Live Face Recognition** - Real-time attendance marking with confidence scores
- **Check-in/Check-out Modes** - Smart attendance tracking with status detection
- **Manual Override Options** - Admin controls for attendance corrections
- **Real-time Statistics** - Live dashboard with attendance metrics

### � Analytics & Reporting
- **Comprehensive Dashboards** - Visual attendance analytics and trends
- **Export Capabilities** - CSV/Excel export for external analysis
- **User Management** - Complete user profile and attendance history
- **System Monitoring** - Real-time system status and health checks

### 🌐 Technical Features
- **WebRTC Integration** - Browser-based camera access without plugins
- **SQLite Database** - Lightweight, file-based data storage with automatic datetime handling
- **Streamlit Interface** - Modern, responsive web application
- **Cross-platform Support** - Windows, macOS, and Linux compatibility

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Virtual environment (recommended)
- Camera/webcam for live registration and attendance

### Installation

1. **Clone/Download the project** and navigate to the project directory:
```bash
cd face_rec
```

2. **Create and activate virtual environment:**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. **Install required packages:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
streamlit run app.py
```

5. **Access the system:**
   - Open browser and go to `http://localhost:8501`
   - Default admin credentials: username=`admin`, password=`admin`

### Important Notes
- **Camera Permissions**: Ensure camera permissions are enabled in your browser
- **WebRTC Support**: Use latest Chrome/Firefox for best live camera features
- **First Run**: Database will be automatically initialized on first startup

## Camera Registration Features

- 📹 **Live WebRTC Camera Streaming** - Real-time video feed in browser
- 👁️ **Real-time Anti-spoofing** - Eye blink detection during registration
- 🎯 **Face Quality Validation** - Automatic face centering and quality checks
- ✅ **Liveness Verification** - MediaPipe-based eye tracking
- 📸 **Auto-capture** - Captures face when all validations pass
- 🔄 **Reset & Retry** - Easy reset for multiple attempts

## Project Structure

```
face_rec/
├── app.py                    # Main Streamlit application
├── auth/
│   ├── __init__.py
│   └── admin_auth.py         # Admin authentication with login form
├── database/
│   ├── __init__.py
│   ├── db_manager.py         # Enhanced database operations with datetime support
│   └── models.py             # Database models and schemas
├── face_detection/           # Face recognition module (renamed to avoid conflicts)
│   ├── __init__.py
│   ├── face_detector.py      # Face detection and recognition logic
│   ├── anti_spoofing.py      # Enhanced eye blink detection with MediaPipe
│   └── face_encoder.py       # Face encoding utilities
├── pages/                    # Application pages (underscore prefix for clean navigation)
│   ├── __init__.py
│   ├── _register.py          # User registration with photo upload
│   ├── _camera_registration.py  # Live camera registration with WebRTC
│   ├── _live_attendance_webrtc.py  # Live attendance with check-in/check-out modes
│   └── _reports.py           # Comprehensive attendance reports and analytics
├── utils/
│   ├── __init__.py
│   └── helpers.py            # System utilities and helper functions
├── data/
│   ├── faces/                # Stored face images for registered users
│   ├── encodings/            # Face encodings cache
│   └── attendance_system.db  # SQLite database (auto-created)
├── .venv/                    # Virtual environment (created during setup)
├── requirements.txt          # Python dependencies
├── config.json              # System configuration
└── README.md                # This documentation
```

## Usage Guide

### 1. **System Access**
- Launch application: `streamlit run app.py`
- Open browser: `http://localhost:8501`
- **Admin Login**: Use credentials `admin` / `admin` (change after first login)

### 2. **User Registration**
**Option A: Live Camera Registration**
- Navigate to "Register Users" → "Live Camera Registration"
- Fill user information (Name, Employee ID, Email, Department)
- Click "Start Camera" and allow browser camera permissions
- Position face in center of camera view (green indicators show good positioning)
- Blink naturally for anti-spoofing verification
- System auto-captures when all validations pass
- Review captured image and submit registration

**Option B: Photo Upload Registration**
- Navigate to "Register Users" → "Photo Upload"
- Fill user information
- Upload clear front-facing photo
- System validates photo quality and extracts face encoding
- Submit registration

### 3. **Live Attendance Tracking**
- Navigate to "Live Attendance"
- Select attendance mode (Check-in/Check-out/Auto-detect)
- Start camera for real-time face recognition
- System automatically marks attendance for recognized faces
- View real-time statistics and recent activity

### 4. **Reports & Analytics**
- Navigate to "Reports & Analytics"
- View attendance summaries and detailed reports
- Filter by date range, department, or individual users
- Export data for external analysis
- Monitor system performance and user statistics

## Technology Stack

- **Frontend**: Streamlit (Web UI Framework)
- **Backend**: Python 3.8+
- **Computer Vision**: OpenCV, face_recognition, MediaPipe
- **Database**: SQLite with automatic datetime handling
- **WebRTC**: streamlit-webrtc for live camera streaming
- **Authentication**: bcrypt for secure password hashing
- **Face Recognition**: dlib-based face encoding and comparison
- **Anti-spoofing**: MediaPipe facial landmarks with custom blink detection

## License

This project is developed for educational and demonstration purposes. Please ensure compliance with local privacy and biometric data regulations when deploying in production environments.

## Support

For issues, questions, or contributions:
1. Check the troubleshooting section above
2. Review the project documentation
3. Test with the provided default setup

---

**Note**: This system processes biometric data. Ensure compliance with applicable privacy laws and regulations such as GDPR, CCPA, or local biometric privacy acts when deploying in production environments.

## Troubleshooting

### Common Issues

**1. Camera Not Working**
- Ensure browser has camera permissions enabled
- Try refreshing the page and allowing camera access
- Use Chrome/Firefox for best WebRTC support
- Check if camera is being used by another application

**2. Face Recognition Issues**
- Ensure good lighting conditions
- Position face clearly in center of camera view
- Remove glasses/masks if possible during registration
- Try re-registering if recognition accuracy is low

**3. Database Errors**
- Database is automatically created on first run
- If issues persist, delete `data/attendance_system.db` to reset
- Ensure write permissions in the project directory

**4. Module Import Errors**
- Activate virtual environment before running
- Reinstall requirements: `pip install -r requirements.txt`
- Check Python version compatibility (3.8+)

### Performance Tips

- **Registration**: Use well-lit environment for best face encoding quality
- **Attendance**: Position camera at eye level for optimal recognition
- **System**: Close unnecessary browser tabs for better camera performance
- **Database**: Regular backup of `data/attendance_system.db` recommended

## Anti-Spoofing Features

- **MediaPipe Eye Tracking** - Advanced facial landmark detection for eye movement
- **Blink Detection Algorithm** - Real-time eye aspect ratio (EAR) calculation
- **Liveness Verification** - Multi-frame validation to prevent static image attacks
- **Quality Assessment** - Face positioning and clarity validation before capture
- **Temporal Analysis** - Movement detection over multiple frames
