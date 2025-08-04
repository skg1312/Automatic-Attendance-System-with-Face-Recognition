import streamlit as st
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
import av
import time
from database.db_manager import DatabaseManager
from face_detection.face_detector import FaceDetector
from face_detection.anti_spoofing import LivenessDetector
from datetime import datetime
import os
import tempfile

# WebRTC configuration
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

class MultiImageRegistrationTransformer(VideoTransformerBase):
    def __init__(self):
        self.face_detector = FaceDetector()
        self.liveness_detector = LivenessDetector()
        self.captured_images = []
        self.max_images = 5
        self.capture_interval = 2  # seconds between captures
        self.last_capture_time = 0
        self.registration_complete = False
        
    def set_user_info(self, name, department, role):
        """Set user information for registration"""
        self.user_name = name
        self.user_department = department
        self.user_role = role
        
    def reset_capture(self):
        """Reset capture state for new registration"""
        self.captured_images = []
        self.last_capture_time = 0
        self.registration_complete = False
        
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        current_time = time.time()
        
        # Detect faces
        detected_faces = self.face_detector.detect_faces_in_frame(img)
        
        # Process liveness detection
        is_live, detection_complete, status_message, processed_frame = self.liveness_detector.process_frame(img)
        
        # Auto-capture logic
        if (detected_faces and len(detected_faces) > 0 and 
            is_live and detection_complete and 
            len(self.captured_images) < self.max_images and
            current_time - self.last_capture_time > self.capture_interval):
            
            # Capture face image
            face_img = self._extract_face_image(img, detected_faces[0])
            if face_img is not None:
                self.captured_images.append({
                    'image': face_img,
                    'timestamp': datetime.now(),
                    'confidence': detected_faces[0][1] if len(detected_faces[0]) > 1 else 0.8
                })
                self.last_capture_time = current_time
                
                # Check if registration is complete
                if len(self.captured_images) >= self.max_images:
                    self.registration_complete = True
        
        # Draw interface
        processed_frame = self._draw_registration_interface(processed_frame, detected_faces, 
                                                          is_live, detection_complete, status_message)
        
        return av.VideoFrame.from_ndarray(processed_frame, format="bgr24")
    
    def _extract_face_image(self, frame, face_info):
        """Extract face region from frame"""
        try:
            name, confidence, location, user_id = face_info
            if location:
                top, right, bottom, left = location
                
                # Add padding around face
                padding = 20
                h, w = frame.shape[:2]
                top = max(0, top - padding)
                bottom = min(h, bottom + padding)
                left = max(0, left - padding)
                right = min(w, right + padding)
                
                face_img = frame[top:bottom, left:right]
                
                # Resize to standard size
                if face_img.size > 0:
                    face_img = cv2.resize(face_img, (150, 150))
                    return face_img
        except:
            pass
        return None
    
    def _draw_registration_interface(self, frame, detected_faces, is_live, detection_complete, status_message):
        """Draw registration interface on frame"""
        h, w = frame.shape[:2]
        
        # Draw status
        status_color = (0, 255, 0) if is_live and detection_complete else (0, 255, 255)
        cv2.putText(frame, status_message, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        # Draw face detection
        if detected_faces and len(detected_faces) > 0:
            name, confidence, location, user_id = detected_faces[0]
            if location:
                top, right, bottom, left = location
                
                # Draw face rectangle
                color = (0, 255, 0) if is_live and detection_complete else (0, 255, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                # Draw confidence
                if confidence > 0:
                    cv2.putText(frame, f"Quality: {confidence:.2f}", (left, top - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw capture progress
        progress_text = f"Captured: {len(self.captured_images)}/{self.max_images}"
        cv2.putText(frame, progress_text, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw progress bar
        bar_width = 300
        bar_height = 20
        bar_x = 10
        bar_y = 80
        
        # Background
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
        
        # Progress
        progress = len(self.captured_images) / self.max_images
        progress_width = int(bar_width * progress)
        if progress_width > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), (0, 255, 0), -1)
        
        # Instructions
        if len(self.captured_images) < self.max_images:
            if is_live and detection_complete and detected_faces and len(detected_faces) > 0:
                instruction = "Look at camera - Auto capturing..."
                color = (0, 255, 0)
            else:
                instruction = "Position face in frame for liveness check"
                color = (0, 255, 255)
        else:
            instruction = "Registration Complete! Click 'Complete Registration'"
            color = (0, 255, 0)
            
        cv2.putText(frame, instruction, (10, h - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Show captured images as thumbnails
        thumb_size = 60
        spacing = 70
        start_x = w - (self.max_images * spacing)
        
        for i, img_data in enumerate(self.captured_images):
            x = start_x + (i * spacing)
            y = 10
            
            # Resize thumbnail
            thumb = cv2.resize(img_data['image'], (thumb_size, thumb_size))
            
            # Place thumbnail
            if x + thumb_size <= w and y + thumb_size <= h:
                frame[y:y+thumb_size, x:x+thumb_size] = thumb
                
                # Draw border
                cv2.rectangle(frame, (x, y), (x+thumb_size, y+thumb_size), (0, 255, 0), 2)
                
                # Draw timestamp
                timestamp = img_data['timestamp'].strftime("%H:%M:%S")
                cv2.putText(frame, timestamp, (x, y+thumb_size+15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        
        return frame
    
    def get_captured_images(self):
        """Get all captured images"""
        return self.captured_images
    
    def is_registration_complete(self):
        """Check if registration is complete"""
        return self.registration_complete

class MultiImageRegistrationPage:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.face_detector = FaceDetector()
        
    def render(self):
        st.title("👥 Multi-Image User Registration")
        st.markdown("Register with multiple face images for better recognition accuracy")
        
        # Registration form
        with st.form("registration_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name*", key="reg_name")
                employee_id = st.text_input("Employee ID*", key="reg_emp_id")
                
            with col2:
                department = st.selectbox("Department*", 
                                        ["Engineering", "HR", "Finance", "Marketing", "Operations", "Other"],
                                        key="reg_dept")
                role = st.selectbox("Role*", 
                                  ["Employee", "Manager", "Team Lead", "Director", "Intern"],
                                  key="reg_role")
            
            email = st.text_input("Email", key="reg_email")
            phone = st.text_input("Phone", key="reg_phone")
            
            submit_form = st.form_submit_button("Start Registration", type="primary")
        
        # Validation and camera activation
        if submit_form:
            if not name or not employee_id or not department or not role:
                st.error("Please fill in all required fields marked with *")
                return
            
            # Check if employee ID already exists
            if self.db_manager.check_employee_id_exists(employee_id):
                st.error(f"Employee ID '{employee_id}' already exists!")
                return
            
            st.session_state.reg_user_info = {
                'name': name,
                'employee_id': employee_id,
                'department': department,
                'role': role,
                'email': email,
                'phone': phone
            }
            st.session_state.start_registration = True
            st.rerun()
        
        # Camera interface
        if hasattr(st.session_state, 'start_registration') and st.session_state.start_registration:
            self._render_camera_interface()
    
    def _render_camera_interface(self):
        """Render the camera interface for multi-image capture"""
        user_info = st.session_state.reg_user_info
        
        st.success(f"Starting registration for: **{user_info['name']}** ({user_info['employee_id']})")
        
        # Instructions
        st.info("""
        📋 **Instructions:**
        1. Position your face clearly in the camera frame
        2. Look directly at the camera for liveness detection
        3. The system will automatically capture 5 images at different angles
        4. Move slightly between captures for better variety
        5. Wait for the green checkmark to complete registration
        """)
        
        # Initialize transformer
        if 'registration_transformer' not in st.session_state:
            st.session_state.registration_transformer = MultiImageRegistrationTransformer()
            st.session_state.registration_transformer.set_user_info(
                user_info['name'], user_info['department'], user_info['role']
            )
        
        # Camera stream
        webrtc_ctx = webrtc_streamer(
            key="multi_image_registration",
            video_transformer_factory=lambda: st.session_state.registration_transformer,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
        
        # Status display
        col1, col2, col3 = st.columns(3)
        
        if webrtc_ctx.video_transformer:
            transformer = webrtc_ctx.video_transformer
            captured_count = len(transformer.get_captured_images())
            
            with col1:
                st.metric("Images Captured", f"{captured_count}/5")
            
            with col2:
                if captured_count > 0:
                    avg_quality = np.mean([img['confidence'] for img in transformer.get_captured_images()])
                    st.metric("Average Quality", f"{avg_quality:.2f}")
                else:
                    st.metric("Average Quality", "0.00")
            
            with col3:
                if transformer.is_registration_complete():
                    st.success("✅ Ready to Complete")
                else:
                    st.info("🔄 Capturing...")
            
            # Complete registration button
            if transformer.is_registration_complete():
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🎯 Complete Registration", type="primary", use_container_width=True):
                        self._complete_registration(transformer.get_captured_images(), user_info)
            
            # Reset button
            if captured_count > 0:
                if st.button("🔄 Reset Capture"):
                    transformer.reset_capture()
                    st.rerun()
        
        # Back button
        if st.button("⬅️ Back to Form"):
            if 'start_registration' in st.session_state:
                del st.session_state.start_registration
            if 'registration_transformer' in st.session_state:
                del st.session_state.registration_transformer
            if 'reg_user_info' in st.session_state:
                del st.session_state.reg_user_info
            st.rerun()
    
    def _complete_registration(self, captured_images, user_info):
        """Complete the registration process with multiple images"""
        try:
            with st.spinner("Processing registration..."):
                # Extract face encodings from all captured images
                face_encodings = []
                
                for img_data in captured_images:
                    img = img_data['image']
                    # Convert to RGB for face_recognition
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    
                    # Get face encoding
                    import face_recognition
                    face_locations = face_recognition.face_locations(rgb_img)
                    if face_locations:
                        encodings = face_recognition.face_encodings(rgb_img, face_locations)
                        if encodings:
                            face_encodings.append(encodings[0])
                
                if not face_encodings:
                    st.error("❌ Could not extract face encodings from captured images!")
                    return
                
                # Register user with multiple encodings
                success = self.db_manager.add_user(
                    name=user_info['name'],
                    employee_id=user_info['employee_id'],
                    department=user_info['department'],
                    email=user_info.get('email', ''),
                    face_encodings=face_encodings,
                    image_path=""
                )
                
                if success:
                    st.success(f"✅ Successfully registered {user_info['name']} with {len(face_encodings)} face encodings!")
                    st.balloons()
                    
                    # Display registration summary
                    st.markdown("### Registration Summary")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Name:** {user_info['name']}")
                        st.write(f"**Employee ID:** {user_info['employee_id']}")
                        st.write(f"**Department:** {user_info['department']}")
                        st.write(f"**Role:** {user_info['role']}")
                    
                    with col2:
                        st.write(f"**Face Encodings:** {len(face_encodings)}")
                        st.write(f"**Images Captured:** {len(captured_images)}")
                        if user_info.get('email'):
                            st.write(f"**Email:** {user_info['email']}")
                        if user_info.get('phone'):
                            st.write(f"**Phone:** {user_info['phone']}")
                    
                    # Clean up session state
                    time.sleep(2)
                    if 'start_registration' in st.session_state:
                        del st.session_state.start_registration
                    if 'registration_transformer' in st.session_state:
                        del st.session_state.registration_transformer
                    if 'reg_user_info' in st.session_state:
                        del st.session_state.reg_user_info
                    
                    st.rerun()
                else:
                    st.error("❌ Failed to register user. Please try again.")
                    
        except Exception as e:
            st.error(f"❌ Registration failed: {str(e)}")

def render_page():
    """Main function to render the multi-image registration page"""
    page = MultiImageRegistrationPage()
    page.render()

if __name__ == "__main__":
    render_page()