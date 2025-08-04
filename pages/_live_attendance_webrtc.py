import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
import av
import cv2
import numpy as np
import time
from datetime import datetime, date
from database.db_manager import DatabaseManager
from face_detection.face_detector import FaceDetector
from face_detection.anti_spoofing import LivenessDetector

# WebRTC configuration for better connectivity
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

class FaceRecognitionTransformer(VideoTransformerBase):
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.face_detector = FaceDetector()
        self.liveness_detector = LivenessDetector()
        
        # Load known faces
        face_data = self.db_manager.get_user_face_encodings()
        self.face_detector.load_known_faces(face_data)
        
        self.confidence_threshold = 0.5
        self.enable_liveness = True
        self.attendance_mode = 'check_in'  # Will be updated from session state
        
        # Performance optimization
        self.frame_skip_count = 0
        self.skip_frames = 3  # Process every 3rd frame for better performance
        self.last_processed_result = []
        
        # Unknown person tracking
        self.unknown_persons = {}
        self.unknown_counter = 0
        
    def set_attendance_mode(self, mode):
        """Set the attendance tracking mode"""
        self.attendance_mode = mode
        
    def _determine_action(self):
        """Determine whether to check in or check out based on mode and time"""
        if self.attendance_mode == 'auto':
            from datetime import datetime
            current_hour = datetime.now().hour
            return 'check_in' if current_hour < 12 else 'check_out'
        else:
            return self.attendance_mode
        
    def _get_attendance_status(self, user_id):
        """Get current attendance status for user today"""
        from datetime import date
        today = date.today()
        
        records = self.db_manager.get_attendance_records(date=today, user_id=user_id)
        if records:
            record = records[0]  # Most recent record for today
            check_in_time = record[4]
            check_out_time = record[5]
            
            if check_in_time and check_out_time:
                return "completed"  # Both check-in and check-out done
            elif check_in_time:
                return "checked_in"  # Only check-in done
            else:
                return "pending"  # No check-in yet
        else:
            return "no_record"  # No attendance record for today
    
    def _handle_unknown_person(self, location):
        """Handle unknown person detection"""
        # Generate unique ID for unknown person based on location
        location_key = f"{location[0]}_{location[1]}_{location[2]}_{location[3]}"
        
        if location_key not in self.unknown_persons:
            self.unknown_counter += 1
            unknown_id = f"Unknown_{self.unknown_counter}"
            self.unknown_persons[location_key] = {
                'id': unknown_id,
                'first_seen': time.time(),
                'last_seen': time.time()
            }
        else:
            self.unknown_persons[location_key]['last_seen'] = time.time()
        
        return self.unknown_persons[location_key]['id']
        
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # Frame skipping for performance
        self.frame_skip_count += 1
        if self.frame_skip_count < self.skip_frames:
            # Use last processed result for intermediate frames
            return self._draw_cached_results(img)
        
        self.frame_skip_count = 0
        
        # Process frame for face recognition with optimization
        detected_faces = self.face_detector.detect_faces_optimized(img, skip_frames=self.skip_frames)
        
        # Process liveness detection if enabled
        if self.enable_liveness and detected_faces and detected_faces[0][0] != "No face detected":
            is_live, detection_complete, status_message, processed_frame = self.liveness_detector.process_frame(img)
        else:
            processed_frame = img.copy()
            is_live = True
            detection_complete = True
            status_message = "Ready for recognition"
        
        # Process detected faces
        recognition_results = []
        for name, location, confidence in detected_faces:
            if name == "No face detected":
                continue
                
            # Handle unknown persons
            if name == "Unknown Person":
                unknown_id = self._handle_unknown_person(location)
                display_name = unknown_id
                color = (0, 0, 255)  # Red for unknown
                user_id = None
            else:
                display_name = name
                color = (0, 255, 0)  # Green for known
                # Get user_id from database
                user_id = self._get_user_id_by_name(name)
            
            recognition_results.append({
                'name': display_name,
                'location': location,
                'confidence': confidence,
                'color': color,
                'user_id': user_id,
                'is_known': name != "Unknown Person"
            })
        
        # Cache results for frame skipping
        self.last_processed_result = recognition_results
        
        # Draw results on frame
        processed_frame = self._draw_recognition_results(processed_frame, recognition_results, 
                                                       is_live, detection_complete, status_message)
        
        return av.VideoFrame.from_ndarray(processed_frame, format="bgr24")
    
    def _get_user_id_by_name(self, name):
        """Get user ID by name from database"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE name = ? AND is_active = 1", (name,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except:
            return None
    
    def _draw_cached_results(self, frame):
        """Draw cached recognition results for skipped frames"""
        if not self.last_processed_result:
            return av.VideoFrame.from_ndarray(frame, format="bgr24")
        
        processed_frame = self._draw_recognition_results(frame, self.last_processed_result, 
                                                       True, True, "Using cached results...")
        return av.VideoFrame.from_ndarray(processed_frame, format="bgr24")
    
    def _draw_recognition_results(self, frame, results, is_live, detection_complete, status_message):
        """Draw recognition results on frame"""
        # Add status text
        status_color = (0, 255, 0) if is_live and detection_complete else (0, 255, 255)
        cv2.putText(frame, status_message, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        # Draw face boxes and labels
        for result in results:
            name = result['name']
            location = result['location']
            confidence = result['confidence']
            color = result['color']
            
            if location:
                top, right, bottom, left = location
                
                # Draw rectangle
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                # Draw label background
                label = f"{name}"
                if confidence > 0:
                    label += f" ({confidence:.2f})"
                
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(frame, (left, bottom - 35), (left + label_size[0], bottom), color, cv2.FILLED)
                
                # Draw label text
                text_color = (255, 255, 255) if result['is_known'] else (255, 255, 255)
                cv2.putText(frame, label, (left + 6, bottom - 6),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
                
                # Handle attendance marking for known persons
                if result['is_known'] and result['user_id'] and confidence >= self.confidence_threshold:
                    if is_live and detection_complete:
                        self._process_attendance(result['user_id'], name, confidence)
        
        # Show unknown persons count
        if len(self.unknown_persons) > 0:
            unknown_text = f"Unknown persons detected: {len(self.unknown_persons)}"
            cv2.putText(frame, unknown_text, (10, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return frame
    
    def _process_attendance(self, user_id, name, confidence):
        """Process attendance marking for recognized user"""
        try:
            action = self._determine_action()
            status = self._get_attendance_status(user_id)
            
            should_mark = False
            message = ""
            
            if action == 'check_in':
                if status in ['no_record', 'pending']:
                    should_mark = True
                    message = f"✅ Check-in: {name}"
                else:
                    message = f"ℹ️ Already checked in: {name}"
            elif action == 'check_out':
                if status == 'checked_in':
                    should_mark = True
                    message = f"✅ Check-out: {name}"
                elif status == 'completed':
                    message = f"ℹ️ Already completed: {name}"
                else:
                    message = f"⚠️ No check-in found: {name}"
            
            if should_mark:
                if action == 'check_in':
                    success = self.db_manager.mark_attendance(user_id, attendance_type='check_in')
                else:
                    success = self.db_manager.mark_attendance(user_id, attendance_type='check_out')
                
                if success:
                    st.session_state.last_attendance_message = message
                    st.session_state.last_attendance_time = datetime.now()
            else:
                st.session_state.last_attendance_message = message
                st.session_state.last_attendance_time = datetime.now()
                
        except Exception as e:
            st.session_state.last_attendance_message = f"❌ Error processing attendance: {str(e)}"
            st.session_state.last_attendance_time = datetime.now()

class LiveAttendancePageWebRTC:
    def __init__(self):
        self.db_manager = DatabaseManager()
        
        # Initialize attendance tracking mode in session state
        if 'attendance_mode' not in st.session_state:
            st.session_state.attendance_mode = 'check_in'
    
    def render(self):
        st.title("🎥 Live Attendance Tracking (WebRTC)")
        st.markdown("Real-time face recognition with anti-spoofing using WebRTC")
        
        # Attendance Mode Selection
        st.markdown("### 🎯 Attendance Mode")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            attendance_mode = st.selectbox(
                "Select Mode:",
                ["check_in", "check_out", "auto"],
                index=["check_in", "check_out", "auto"].index(st.session_state.attendance_mode),
                help="Choose attendance tracking mode"
            )
            st.session_state.attendance_mode = attendance_mode
        
        with col2:
            if attendance_mode == "auto":
                st.info("🤖 Auto mode: Check-in before 12:00 PM, Check-out after 12:00 PM")
            elif attendance_mode == "check_in":
                st.success("🟢 Check-in mode: Marking arrivals")
            else:
                st.warning("🔴 Check-out mode: Marking departures")
        
        with col3:
            if st.button("🔄 Reset Today's Status"):
                # Option to reset attendance status for testing
                st.info("Reset functionality - for admin use")
        
        # Settings
        st.markdown("### ⚙️ Camera Settings")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            confidence_threshold = st.slider("Recognition Confidence", 0.5, 0.9, 0.6, 0.05)
        
        with col2:
            enable_liveness = st.checkbox("Enable Anti-Spoofing", value=True)
        
        with col3:
            auto_mark = st.checkbox("Auto Mark Attendance", value=True)
        
        # WebRTC Video Stream
        st.markdown("### 📹 Live Camera Feed")
        
        ctx = webrtc_streamer(
            key="face-recognition",
            video_transformer_factory=FaceRecognitionTransformer,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
        
        # Update transformer settings
        if ctx.video_transformer:
            ctx.video_transformer.confidence_threshold = confidence_threshold
            ctx.video_transformer.enable_liveness = enable_liveness
            ctx.video_transformer.set_attendance_mode(attendance_mode)
        
        # Control panel
        st.markdown("### 🎛️ Controls")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Reload Face Database"):
                if ctx.video_transformer:
                    face_data = self.db_manager.get_user_face_encodings()
                    ctx.video_transformer.face_detector.load_known_faces(face_data)
                    st.success(f"Loaded {len(face_data)} face encodings")
        
        with col2:
            if st.button("🧹 Reset Liveness"):
                if ctx.video_transformer:
                    ctx.video_transformer.liveness_detector.reset()
                    st.success("Liveness detector reset")
        
        with col3:
            st.metric("📊 Camera Status", "🟢 Active" if ctx.state.playing else "🔴 Stopped")
        
        with col4:
            mode_color = {"check_in": "🟢", "check_out": "🔴", "auto": "🔵"}
            st.metric("🎯 Mode", f"{mode_color.get(attendance_mode, '⚪')} {attendance_mode.title()}")
        
        # Today's attendance
        self._show_todays_attendance()
        
        # Today's attendance statistics
        self._show_attendance_stats()
    
    def _show_todays_attendance(self):
        """Show today's attendance records with proper datetime handling"""
        st.markdown("### 📋 Today's Attendance")
        
        from datetime import date
        try:
            today_records = self.db_manager.get_attendance_records(date=date.today())
        except Exception as e:
            st.error(f"Error fetching attendance records: {e}")
            return
        
        if not today_records:
            st.info("No attendance records for today yet.")
            return
        
        # Process records for display
        attendance_data = []
        for record in today_records:
            try:
                record_id, name, employee_id, department, check_in, check_out, date_val, confidence = record
                
                # Handle datetime conversion for check_in
                if check_in:
                    if isinstance(check_in, str):
                        try:
                            from datetime import datetime
                            check_in_dt = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
                            check_in_str = check_in_dt.strftime("%H:%M:%S")
                        except:
                            check_in_str = str(check_in)
                    else:
                        check_in_str = check_in.strftime("%H:%M:%S")
                else:
                    check_in_str = "Not checked in"
                
                # Handle datetime conversion for check_out
                if check_out:
                    if isinstance(check_out, str):
                        try:
                            from datetime import datetime
                            check_out_dt = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
                            check_out_str = check_out_dt.strftime("%H:%M:%S")
                        except:
                            check_out_str = str(check_out)
                    else:
                        check_out_str = check_out.strftime("%H:%M:%S")
                else:
                    check_out_str = "Not checked out"
                
                attendance_data.append({
                    "Name": name,
                    "Employee ID": employee_id,
                    "Department": department or "N/A",
                    "Check In": check_in_str,
                    "Check Out": check_out_str,
                    "Confidence": f"{confidence:.2f}" if confidence else "N/A"
                })
            except Exception as e:
                st.warning(f"Error processing record: {e}")
                continue
        
        # Display as dataframe
        if attendance_data:
            st.dataframe(attendance_data, use_container_width=True)
        else:
            st.info("No valid attendance records to display.")
    
    def _show_attendance_stats(self):
        """Show today's attendance statistics"""
        st.markdown("### 📊 Today's Attendance Statistics")
        
        from datetime import date
        try:
            today_records = self.db_manager.get_attendance_records(date=date.today())
            
            # Calculate statistics
            total_users = len(self.db_manager.get_all_users())
            total_records = len(today_records)
            
            # Count check-ins and check-outs
            check_ins = 0
            check_outs = 0
            completed_attendance = 0
            
            user_status = {}
            
            for record in today_records:
                user_id = record[0]
                check_in = record[4]
                check_out = record[5]
                
                if check_in:
                    check_ins += 1
                    user_status[user_id] = 'checked_in'
                
                if check_out:
                    check_outs += 1
                    if user_id in user_status:
                        user_status[user_id] = 'completed'
                        completed_attendance += 1
            
            # Display metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("👥 Total Users", total_users)
            
            with col2:
                st.metric("✅ Check-ins", check_ins)
            
            with col3:
                st.metric("🚪 Check-outs", check_outs)
            
            with col4:
                st.metric("✔️ Completed", completed_attendance)
            
            with col5:
                attendance_rate = (check_ins / total_users * 100) if total_users > 0 else 0
                st.metric("📈 Attendance Rate", f"{attendance_rate:.1f}%")
            
            # Show status breakdown
            if user_status:
                st.markdown("#### 📋 User Status Breakdown")
                status_counts = {
                    'checked_in': sum(1 for status in user_status.values() if status == 'checked_in'),
                    'completed': sum(1 for status in user_status.values() if status == 'completed'),
                    'not_present': total_users - len(user_status)
                }
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"🟡 Checked In Only: {status_counts['checked_in']}")
                with col2:
                    st.success(f"🟢 Completed (In+Out): {status_counts['completed']}")
                with col3:
                    st.warning(f"🔴 Not Present: {status_counts['not_present']}")
            
        except Exception as e:
            st.error(f"Error calculating attendance statistics: {e}")

if __name__ == "__main__":
    page = LiveAttendancePageWebRTC()
    page.render()
