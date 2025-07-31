import streamlit as st
import cv2
import numpy as np
from PIL import Image
import os
from datetime import datetime
import time
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
import av
from database.db_manager import DatabaseManager
from face_detection.face_detector import FaceDetector
from face_detection.anti_spoofing import LivenessDetector

# WebRTC configuration
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

class FaceRegistrationTransformer(VideoTransformerBase):
    def __init__(self):
        self.face_detector = FaceDetector()
        self.liveness_detector = LivenessDetector()
        self.captured_frame = None
        self.face_encoding = None
        self.capture_requested = False
        self.registration_complete = False
        self.status_message = "Position your face in the center and look at camera"
        
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # Process frame for face validation and liveness
        face_valid, face_message = self.face_detector.validate_face_quality(img)
        is_live, detection_complete, liveness_message, processed_frame = self.liveness_detector.process_frame(img)
        
        # Update status message
        if not face_valid:
            self.status_message = face_message
            color = (0, 0, 255)  # Red
        elif not detection_complete:
            self.status_message = liveness_message
            color = (255, 255, 0)  # Yellow
        elif detection_complete and is_live and face_valid:
            self.status_message = "✅ Ready to capture! Click 'Capture Face' button"
            color = (0, 255, 0)  # Green
            
            # Auto-capture if requested
            if self.capture_requested and not self.registration_complete:
                self.captured_frame = img.copy()
                self.face_encoding = self.face_detector.encode_face_from_frame(img)
                self.registration_complete = True
                self.status_message = "✅ Face captured successfully!"
                self.capture_requested = False
        else:
            self.status_message = "❌ Liveness check failed - please blink naturally"
            color = (0, 0, 255)  # Red
        
        # Add status text to frame
        cv2.putText(processed_frame, self.status_message, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Add instruction text
        cv2.putText(processed_frame, "Look directly at camera and blink naturally", (10, processed_frame.shape[0] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return av.VideoFrame.from_ndarray(processed_frame, format="bgr24")
    
    def request_capture(self):
        """Request face capture on next valid frame"""
        self.capture_requested = True
        self.liveness_detector.reset()
    
    def reset(self):
        """Reset the transformer state"""
        self.captured_frame = None
        self.face_encoding = None
        self.capture_requested = False
        self.registration_complete = False
        self.liveness_detector.reset()
        self.status_message = "Position your face in the center and look at camera"

class CameraRegistrationPage:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def render(self):
        st.title("📷 Camera Registration")
        st.markdown("Register new users using live camera with anti-spoofing verification")
        
        # User information form
        with st.form("user_info_form", clear_on_submit=False):
            st.subheader("👤 User Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name*", placeholder="Enter full name", key="reg_name")
                employee_id = st.text_input("Employee/Student ID*", placeholder="Enter unique ID", key="reg_id")
            
            with col2:
                email = st.text_input("Email", placeholder="Enter email address", key="reg_email")
                department = st.text_input("Department", placeholder="Enter department", key="reg_dept")
            
            # Form validation
            form_valid = bool(name and employee_id)
            
            if not form_valid:
                st.warning("⚠️ Please fill in Name and Employee ID before starting camera")
            
            start_registration = st.form_submit_button("📷 Start Camera Registration", disabled=not form_valid)
        
        # Camera registration process
        if start_registration and form_valid:
            self._handle_camera_registration(name, employee_id, email, department)
    
    def _handle_camera_registration(self, name, employee_id, email, department):
        """Handle the camera registration process"""
        st.subheader("📹 Live Camera Registration")
        
        # Instructions
        with st.expander("📋 Registration Instructions", expanded=True):
            st.markdown("""
            **Steps to complete registration:**
            1. **Position yourself**: Center your face in the camera view
            2. **Look directly**: Face the camera straight on
            3. **Natural lighting**: Ensure good, even lighting on your face
            4. **Blink naturally**: The system will detect eye blinks for liveness verification
            5. **Stay still**: Once validation is complete, the system will capture automatically
            6. **Review**: Check the captured image and submit registration
            
            **Requirements:**
            - Only one person should be visible
            - Face should be clearly visible and well-lit
            - Distance: 0.5-2 meters from camera
            - Look directly at the camera lens
            """)
        
        # WebRTC camera stream
        ctx = webrtc_streamer(
            key="face-registration",
            video_transformer_factory=FaceRegistrationTransformer,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
        
        # Control buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📸 Capture Face", type="primary", disabled=not ctx.video_transformer):
                if ctx.video_transformer:
                    ctx.video_transformer.request_capture()
                    st.info("Capture requested - please wait for validation...")
        
        with col2:
            if st.button("🔄 Reset", disabled=not ctx.video_transformer):
                if ctx.video_transformer:
                    ctx.video_transformer.reset()
                    st.info("Registration reset - position your face again")
        
        with col3:
            if st.button("⏹️ Stop Camera"):
                st.rerun()
        
        # Show current status
        if ctx.video_transformer:
            status_placeholder = st.empty()
            status_placeholder.info(f"**Status:** {ctx.video_transformer.status_message}")
            
            # Check if capture is complete
            if ctx.video_transformer.registration_complete and ctx.video_transformer.captured_frame is not None:
                self._process_captured_face(ctx.video_transformer, name, employee_id, email, department)
    
    def _process_captured_face(self, transformer, name, employee_id, email, department):
        """Process the captured face and complete registration"""
        st.success("✅ Face captured successfully!")
        
        # Display captured image
        st.subheader("📸 Captured Face")
        captured_image = transformer.captured_frame
        st.image(captured_image, channels="BGR", caption=f"Captured: {name}", width=400)
        
        # Show registration details
        with st.expander("📋 Registration Preview", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Name:** {name}")
                st.write(f"**Employee ID:** {employee_id}")
            
            with col2:
                st.write(f"**Email:** {email or 'Not provided'}")
                st.write(f"**Department:** {department or 'Not provided'}")
        
        # Final registration buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Confirm Registration", type="primary"):
                self._save_registration(transformer, name, employee_id, email, department)
        
        with col2:
            if st.button("📸 Recapture"):
                transformer.reset()
                st.rerun()
        
        with col3:
            if st.button("❌ Cancel"):
                transformer.reset()
                st.rerun()
    
    def _save_registration(self, transformer, name, employee_id, email, department):
        """Save the registration to database"""
        try:
            # Get face encoding
            face_encoding = transformer.face_encoding
            captured_frame = transformer.captured_frame
            
            if face_encoding is None:
                st.error("❌ Failed to extract face encoding. Please try again.")
                return
            
            # Save face image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{employee_id}_{timestamp}.jpg"
            image_path = os.path.join("data/faces", image_filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
            # Save image
            cv2.imwrite(image_path, captured_frame)
            
            # Register user in database
            user_id = self.db_manager.add_user(
                name=name,
                employee_id=employee_id,
                email=email,
                department=department,
                face_encoding=face_encoding,
                image_path=image_path
            )
            
            if user_id:
                st.success(f"🎉 Registration successful!")
                st.balloons()
                
                # Show success details
                with st.container():
                    st.markdown("### ✅ Registration Complete")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"""
                        **User registered successfully!**
                        - **Name:** {name}
                        - **ID:** {employee_id}
                        - **Database ID:** {user_id}
                        - **Registration Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        """)
                    
                    with col2:
                        st.image(captured_frame, channels="BGR", caption="Registered Photo", width=300)
                
                # Options for next steps
                st.markdown("### 🚀 Next Steps")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("👥 Register Another User"):
                        # Clear registration data and reset
                        if 'camera_user_info' in st.session_state:
                            del st.session_state['camera_user_info']
                        transformer.reset()
                        st.rerun()
                
                with col2:
                    if st.button("🎥 Go to Live Attendance"):
                        # Set navigation to Live Attendance page
                        st.session_state.current_page = "🎥 Live Attendance"
                        st.success("✅ Registration completed! Redirecting to Live Attendance...")
                        st.rerun()
                
                with col3:
                    if st.button("📊 View Reports"):
                        # Set navigation to Reports page
                        st.session_state.current_page = "📊 Reports & Analytics"
                        st.success("✅ Registration completed! Redirecting to Reports...")
                        st.rerun()
                
            else:
                st.error("❌ Registration failed. Employee ID might already exist.")
                # Clean up saved image
                if os.path.exists(image_path):
                    os.remove(image_path)
                
        except Exception as e:
            st.error(f"❌ Registration error: {str(e)}")
            st.info("Please try again or contact system administrator.")

if __name__ == "__main__":
    page = CameraRegistrationPage()
    page.render()
