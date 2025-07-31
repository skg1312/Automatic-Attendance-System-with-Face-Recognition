import streamlit as st
import cv2
import numpy as np
from PIL import Image
import os
from datetime import datetime
from database.db_manager import DatabaseManager
from face_detection.face_detector import FaceDetector
from face_detection.anti_spoofing import LivenessDetector

class RegisterPage:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.face_detector = FaceDetector()
        self.liveness_detector = LivenessDetector()
    
    def render(self):
        st.title("👥 Register New Person")
        st.markdown("Add new students or employees to the attendance system")
        
        # Create tabs for different registration methods
        tab1, tab2, tab3 = st.tabs(["📷 Live Camera Registration", "📁 Upload Photo", "👥 View Registered Users"])
        
        with tab1:
            self._camera_registration_webrtc()
        
        with tab2:
            self._upload_registration()
        
        with tab3:
            self.show_registered_users()
    
    def _camera_registration_webrtc(self):
        """WebRTC-based camera registration with user details form"""
        st.subheader("📷 Live Camera Registration")
        st.markdown("Real-time face capture with anti-spoofing verification")
        
        # User details form first
        with st.form("camera_registration_form"):
            st.markdown("### 👤 Personal Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name*", placeholder="Enter full name")
                employee_id = st.text_input("Employee/Student ID*", placeholder="Enter unique ID")
            
            with col2:
                email = st.text_input("Email", placeholder="Enter email address")
                department = st.text_input("Department", placeholder="Enter department")
            
            submit_info = st.form_submit_button("💾 Save Info & Continue to Camera")
            
            if submit_info and name and employee_id:
                # Store user info in session state
                st.session_state['camera_user_info'] = {
                    'name': name,
                    'employee_id': employee_id,
                    'email': email,
                    'department': department
                }
                st.success("✅ Information saved! Now proceed to camera capture below.")
            elif submit_info:
                st.error("❌ Please fill in the required fields (Name and Employee ID)")
        
        # Camera capture section (only show if user info is saved)
        if 'camera_user_info' in st.session_state:
            user_info = st.session_state['camera_user_info']
            
            st.markdown("### 📸 Camera Capture")
            st.info(f"📋 Registering: **{user_info['name']}** (ID: {user_info['employee_id']})")
            
            # Check if streamlit-webrtc is available
            try:
                from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
                import av
                
                # Import the camera registration page
                from pages._camera_registration import CameraRegistrationPage
                
                # Render the camera registration interface with user info
                camera_page = CameraRegistrationPage()
                camera_page._handle_camera_registration(
                    user_info['name'], 
                    user_info['employee_id'], 
                    user_info['email'], 
                    user_info['department']
                )
                
            except ImportError:
                st.warning("📦 WebRTC component not available")
                st.markdown("""
                **To enable live camera registration:**
                
                1. Install the WebRTC component:
                ```bash
                pip install streamlit-webrtc
                ```
                
                2. Restart the application
                
                **Alternative:** Use the 'Upload Photo' tab for now.
                """)
                
                # Store info for upload tab
                st.session_state['pending_registration'] = user_info
        else:
            st.info("👆 Please fill in your information above first, then camera capture will be available.")
    
    
    def _camera_registration_fallback(self):
        """Fallback camera registration instructions"""
        st.subheader("📷 Camera Registration (Manual)")
        
        with st.form("camera_fallback_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name*", placeholder="Enter full name")
                employee_id = st.text_input("Employee/Student ID*", placeholder="Enter unique ID")
            
            with col2:
                email = st.text_input("Email", placeholder="Enter email address")
                department = st.text_input("Department", placeholder="Enter department")
            
            st.markdown("### 📸 Camera Capture Instructions")
            st.info("""
            **Since live camera is not available, please:**
            
            1. **Take a photo** using your device's camera app
            2. **Save the photo** to your computer
            3. **Switch to 'Upload Photo' tab** to complete registration
            
            **Photo Requirements:**
            - Clear face visible and well-lit
            - Only one person in the photo
            - Face looking directly at camera
            - Distance: 0.5-2 meters from camera
            - Good lighting conditions
            """)
            
            submit_manual = st.form_submit_button("� Note Information (Use Upload Tab)")
            
            if submit_manual and name and employee_id:
                # Store in session state for upload tab
                st.session_state['pending_registration'] = {
                    'name': name,
                    'employee_id': employee_id,
                    'email': email,
                    'department': department
                }
                st.success("ℹ️ Information noted. Please use 'Upload Photo' tab to complete registration.")
            elif submit_manual:
                st.error("Please fill in the required fields (Name and Employee ID)")
    
    def _handle_camera_capture(self, name, employee_id, email, department):
        """Handle camera capture with liveness detection"""
        # Create placeholder for camera feed
        camera_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Initialize camera
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            st.error("Unable to access camera. Please check camera permissions.")
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Reset liveness detector
        self.liveness_detector.reset()
        
        capture_complete = False
        face_encoding = None
        captured_frame = None
        
        # Control buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔴 Stop Camera"):
                cap.release()
                camera_placeholder.empty()
                status_placeholder.empty()
                return
        
        with col2:
            capture_button = st.button("📸 Capture Face")
        
        with col3:
            if st.button("🔄 Reset"):
                self.liveness_detector.reset()
        
        # Main capture loop
        frame_count = 0
        while not capture_complete:
            ret, frame = cap.read()
            
            if not ret:
                st.error("Failed to read from camera")
                break
            
            frame_count += 1
            
            # Mirror the frame
            frame = cv2.flip(frame, 1)
            
            # Process frame for liveness detection
            is_live, detection_complete, status_message, processed_frame = self.liveness_detector.process_frame(frame)
            
            # Validate face quality
            face_valid, face_message = self.face_detector.validate_face_quality(frame)
            
            # Add face validation message to frame
            color = (0, 255, 0) if face_valid else (0, 0, 255)
            cv2.putText(processed_frame, face_message, (10, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Display frame
            camera_placeholder.image(processed_frame, channels="BGR", use_column_width=True)
            
            # Update status
            status_placeholder.info(f"**Status:** {status_message}")
            
            # Check if capture should be triggered
            if capture_button or (detection_complete and is_live and face_valid):
                if face_valid:
                    # Extract face encoding
                    face_encoding = self.face_detector.encode_face_from_frame(frame)
                    
                    if face_encoding is not None:
                        captured_frame = frame.copy()
                        capture_complete = True
                        status_placeholder.success("✅ Face captured successfully!")
                    else:
                        status_placeholder.error("❌ Failed to extract face encoding. Please try again.")
                else:
                    status_placeholder.error(f"❌ {face_message}")
            
            # Break if user stops
            if frame_count > 1000:  # Prevent infinite loop
                break
        
        # Cleanup camera
        cap.release()
        
        # Process registration if successful
        if face_encoding is not None and captured_frame is not None:
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
                st.success(f"✅ User '{name}' registered successfully with ID: {user_id}")
                
                # Display captured image
                st.subheader("📸 Captured Image")
                st.image(captured_frame, channels="BGR", caption=f"Registered: {name}", use_column_width=True)
                
                # Show registration details
                with st.expander("📋 Registration Details"):
                    st.write(f"**Name:** {name}")
                    st.write(f"**Employee ID:** {employee_id}")
                    st.write(f"**Email:** {email}")
                    st.write(f"**Department:** {department}")
                    st.write(f"**Registration Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Image Path:** {image_path}")
            else:
                st.error("❌ Registration failed. Employee ID might already exist.")
                # Clean up saved image
                if os.path.exists(image_path):
                    os.remove(image_path)
    
    def _upload_registration(self):
        """Photo upload based registration"""
        st.subheader("Register using Photo Upload")
        
        # Check if there's pending registration info from camera tab
        pending_info = st.session_state.get('pending_registration', {})
        
        with st.form("upload_registration_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name*", 
                                   value=pending_info.get('name', ''),
                                   placeholder="Enter full name", 
                                   key="upload_name")
                employee_id = st.text_input("Employee/Student ID*", 
                                           value=pending_info.get('employee_id', ''),
                                           placeholder="Enter unique ID", 
                                           key="upload_id")
            
            with col2:
                email = st.text_input("Email", 
                                     value=pending_info.get('email', ''),
                                     placeholder="Enter email address", 
                                     key="upload_email")
                department = st.text_input("Department", 
                                          value=pending_info.get('department', ''),
                                          placeholder="Enter department", 
                                          key="upload_dept")
            
            # Clear pending info if it was used
            if pending_info:
                st.info("ℹ️ Information pre-filled from camera registration tab")
            
            # File upload
            uploaded_file = st.file_uploader(
                "Choose a face image",
                type=['jpg', 'jpeg', 'png'],
                help="Upload a clear photo showing the person's face"
            )
            
            # Photo requirements
            with st.expander("📋 Photo Requirements"):
                st.markdown("""
                **For best results, ensure your photo has:**
                - ✅ Clear face visible and well-lit
                - ✅ Only one person in the photo
                - ✅ Face looking directly at camera
                - ✅ Distance: 0.5-2 meters from camera
                - ✅ Good lighting conditions (avoid shadows)
                - ✅ High resolution (minimum 300x300 pixels)
                - ✅ File size under 10MB
                """)
            
            submit_upload = st.form_submit_button("📤 Register with Photo")
            
            if submit_upload and uploaded_file and name and employee_id:
                # Clear pending registration
                if 'pending_registration' in st.session_state:
                    del st.session_state['pending_registration']
                self._process_uploaded_image(uploaded_file, name, employee_id, email, department)
            elif submit_upload:
                st.error("Please fill in all required fields and upload an image")
    
    def _process_uploaded_image(self, uploaded_file, name, employee_id, email, department):
        """Process uploaded image for registration"""
        try:
            # Convert uploaded file to opencv format
            image = Image.open(uploaded_file)
            image_array = np.array(image)
            
            # Convert RGB to BGR if needed
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # Validate face quality
            face_valid, face_message = self.face_detector.validate_face_quality(image_array)
            
            if not face_valid:
                st.error(f"❌ {face_message}")
                st.image(image, caption="Uploaded Image", use_column_width=True)
                return
            
            # Extract face encoding
            face_encoding = self.face_detector.encode_face_from_frame(image_array)
            
            if face_encoding is None:
                st.error("❌ No face detected in the uploaded image. Please upload a clear face photo.")
                return
            
            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{employee_id}_{timestamp}.jpg"
            image_path = os.path.join("data/faces", image_filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
            # Save image
            cv2.imwrite(image_path, image_array)
            
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
                st.success(f"✅ User '{name}' registered successfully with ID: {user_id}")
                
                # Display processed image with face detection
                detected_faces = self.face_detector.detect_faces_in_frame(image_array)
                if detected_faces:
                    processed_image = self.face_detector.draw_face_boxes(image_array.copy(), [(name, 1.0, detected_faces[0][2], user_id)])
                    st.image(processed_image, channels="BGR", caption="Registered Face", use_column_width=True)
                else:
                    st.image(image, caption="Registered Image", use_column_width=True)
                
                # Show registration details
                with st.expander("📋 Registration Details"):
                    st.write(f"**Name:** {name}")
                    st.write(f"**Employee ID:** {employee_id}")
                    st.write(f"**Email:** {email}")
                    st.write(f"**Department:** {department}")
                    st.write(f"**Registration Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Navigation options after successful registration
                st.markdown("### 🚀 What's Next?")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("👥 Register Another User", key="upload_register_another"):
                        # Clear session data for new registration
                        if 'pending_registration' in st.session_state:
                            del st.session_state['pending_registration']
                        st.rerun()
                
                with col2:
                    if st.button("🎥 Test Live Attendance", key="upload_test_attendance"):
                        st.session_state.current_page = "🎥 Live Attendance"
                        st.success("✅ Redirecting to Live Attendance...")
                        st.rerun()
                
                with col3:
                    if st.button("📊 View Reports", key="upload_view_reports"):
                        st.session_state.current_page = "📊 Reports & Analytics"
                        st.success("✅ Redirecting to Reports...")
                        st.rerun()
            else:
                st.error("❌ Registration failed. Employee ID might already exist.")
                # Clean up saved image
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
        except Exception as e:
            st.error(f"❌ Error processing image: {str(e)}")
    
    def show_registered_users(self):
        """Display all registered users"""
        st.subheader("📋 Registered Users")
        
        users = self.db_manager.get_all_users()
        
        if not users:
            st.info("No users registered yet.")
            return
        
        # Display users in a table
        user_data = []
        for user in users:
            user_id, name, employee_id, email, department, image_path, created_at = user
            user_data.append({
                "ID": user_id,
                "Name": name,
                "Employee ID": employee_id,
                "Email": email or "N/A",
                "Department": department or "N/A",
                "Registered": created_at
            })
        
        st.dataframe(user_data, use_container_width=True)
        
        # User management options
        with st.expander("👥 User Management"):
            selected_user_id = st.selectbox(
                "Select user to manage:",
                options=[user[0] for user in users],
                format_func=lambda x: f"{dict([(u[0], f'{u[1]} ({u[2]})') for u in users]).get(x, x)}"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Delete User"):
                    if self.db_manager.delete_user(selected_user_id):
                        st.success("User deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete user")
            
            with col2:
                if st.button("📷 View Photo"):
                    # Find user details
                    user_details = next((u for u in users if u[0] == selected_user_id), None)
                    if user_details and user_details[5]:  # image_path
                        image_path = user_details[5]
                        if os.path.exists(image_path):
                            image = cv2.imread(image_path)
                            st.image(image, channels="BGR", caption=f"Photo: {user_details[1]}", width=300)
                        else:
                            st.error("Image file not found")
                    else:
                        st.error("No image available for this user")
