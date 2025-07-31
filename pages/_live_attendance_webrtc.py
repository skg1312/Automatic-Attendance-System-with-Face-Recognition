import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
import av
import cv2
import numpy as np
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
        
        self.confidence_threshold = 0.6
        self.enable_liveness = True
        self.attendance_mode = 'check_in'  # Will be updated from session state
        
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
        
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # Process frame for face recognition
        detected_faces = self.face_detector.detect_faces_in_frame(img, scale_factor=0.5)
        
        # Process liveness detection if enabled
        if self.enable_liveness and detected_faces:
            is_live, detection_complete, status_message, processed_frame = self.liveness_detector.process_frame(img)
        else:
            processed_frame = img.copy()
            is_live = True
            detection_complete = True
            status_message = "Liveness detection disabled"
        
        # Draw face boxes and information
        if detected_faces:
            processed_frame = self.face_detector.draw_face_boxes(processed_frame, detected_faces)
            
            # Add status text
            cv2.putText(processed_frame, status_message, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Process recognitions for attendance
            for name, confidence, location, user_id in detected_faces:
                if confidence >= self.confidence_threshold and is_live and detection_complete:
                    
                    # Determine action based on mode
                    action = self._determine_action()
                    
                    # Get current attendance status
                    status = self._get_attendance_status(user_id)
                    
                    # Determine if attendance should be marked
                    should_mark = False
                    message = ""
                    
                    if action == 'check_in':
                        if status in ['no_record', 'pending']:
                            should_mark = True
                            message = f"✅ CHECK-IN: {name}"
                        else:
                            message = f"ℹ️ Already checked in: {name}"
                    elif action == 'check_out':
                        if status == 'checked_in':
                            should_mark = True
                            message = f"🚪 CHECK-OUT: {name}"
                        elif status == 'completed':
                            message = f"ℹ️ Already checked out: {name}"
                        else:
                            message = f"⚠️ Must check in first: {name}"
                    
                    # Mark attendance if appropriate
                    if should_mark:
                        success = self.db_manager.mark_attendance(user_id, confidence, action)
                        if success:
                            cv2.putText(processed_frame, message, (10, 60),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        else:
                            cv2.putText(processed_frame, f"❌ Error marking attendance: {name}", (10, 60),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    else:
                        cv2.putText(processed_frame, message, (10, 60),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    # Show attendance mode
                    cv2.putText(processed_frame, f"Mode: {action.upper()}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return av.VideoFrame.from_ndarray(processed_frame, format="bgr24")

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
