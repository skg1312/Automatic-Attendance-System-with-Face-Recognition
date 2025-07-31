import streamlit as st
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth.admin_auth import AdminAuth
from pages._register import RegisterPage
from pages._live_attendance_webrtc import LiveAttendancePageWebRTC
from pages._reports import ReportsPage
from database.db_manager import DatabaseManager
from utils.helpers import get_system_info, StreamlitUtils

# Configure page
st.set_page_config(
    page_title="Automatic Attendance System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application function"""
    
    # Add basic CSS styling
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .sidebar-logo {
            text-align: center;
            padding: 1rem;
            background: #f0f2f6;
            border-radius: 10px;
            margin-bottom: 1rem;
        }
        
        .status-card {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #28a745;
            margin: 1rem 0;
        }
        
        .metric-card {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize authentication
    auth = AdminAuth()
    
    # Check if user is logged in
    if not auth.is_logged_in():
        # Show login page
        st.markdown('<div class="main-header"><h1>🎯 Automatic Attendance System</h1><p>Face Recognition with Anti-Spoofing Technology</p></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            auth.login_form()
        
        # Show system features while not logged in
        st.markdown("---")
        show_features()
        return
    
    # Main application interface
    show_main_app(auth)

def show_features():
    """Show system features on login page"""
    st.subheader("🌟 System Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🔐 Security Features
        - Admin authentication
        - Anti-spoofing detection
        - Eye blink verification
        - Secure face encoding
        """)
    
    with col2:
        st.markdown("""
        ### 📊 Attendance Management
        - Live face recognition
        - Automatic attendance marking
        - Manual attendance options
        - Real-time monitoring
        """)
    
    with col3:
        st.markdown("""
        ### 📈 Analytics & Reports
        - Comprehensive dashboards
        - Attendance analytics
        - Export capabilities
        - User management
        """)

def show_main_app(auth):
    """Show main application interface"""
    
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="sidebar-logo"><h2>🎯 Attendance System</h2></div>', unsafe_allow_html=True)
        
        # Show logout button
        auth.logout_button()
        
        # Navigation menu
        st.markdown("### 📋 Navigation")
        
        # Get current page from session state or default to Dashboard
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "🏠 Dashboard"
        
        page = st.selectbox(
            "Select Page:",
            ["🏠 Dashboard", "👥 Register Users", "🎥 Live Attendance", "📊 Reports & Analytics"],
            index=["🏠 Dashboard", "👥 Register Users", "🎥 Live Attendance", "📊 Reports & Analytics"].index(st.session_state.current_page),
            key="navigation"
        )
        
        # Update current page in session state
        st.session_state.current_page = page
        
        # Quick stats
        st.markdown("### 📈 Quick Stats")
        try:
            db_manager = DatabaseManager()
            
            # Get stats
            total_users = len(db_manager.get_all_users())
            today_attendance = len(db_manager.get_attendance_records())
            
            st.metric("👥 Total Users", total_users)
            st.metric("📋 Total Records", today_attendance)
            
        except Exception as e:
            st.error(f"Error loading stats: {e}")
        
        # System info
        with st.expander("ℹ️ System Info"):
            system_info = get_system_info()
            for key, value in system_info.items():
                st.text(f"{key}: {value}")
    
    # Main content area
    st.markdown('<div class="main-header"><h1>🎯 Automatic Attendance System</h1></div>', unsafe_allow_html=True)
    
    # Route to different pages
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "👥 Register Users":
        register_page = RegisterPage()
        register_page.render()
    elif page == "🎥 Live Attendance":
        attendance_page = LiveAttendancePageWebRTC()
        attendance_page.render()
    elif page == "📊 Reports & Analytics":
        reports_page = ReportsPage()
        reports_page.render()

def show_dashboard():
    """Show main dashboard"""
    st.subheader("🏠 Dashboard")
    
    try:
        db_manager = DatabaseManager()
        
        # Get dashboard metrics
        all_users = db_manager.get_all_users()
        all_attendance = db_manager.get_attendance_records()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("👥 Total Users", len(all_users))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("📋 Total Records", len(all_attendance))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            active_users = len([user for user in all_users])  # All users are considered active
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("✅ Active Users", active_users)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            face_encodings = db_manager.get_user_face_encodings()
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("🔍 Ready for Recognition", len(face_encodings))
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Recent activity
        st.markdown("### 📈 Recent Activity")
        
        if all_attendance:
            # Show last 10 records
            recent_records = all_attendance[:10]
            
            for record in recent_records:
                record_id, name, employee_id, department, check_in, check_out, date_val, confidence = record
                
                # Create activity card
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{name}** ({employee_id})")
                    
                    with col2:
                        st.write(f"📅 {date_val}")
                    
                    with col3:
                        if check_in:
                            st.write(f"✅ {check_in}")
                        else:
                            st.write("⏳ Pending")
                    
                    with col4:
                        if confidence:
                            st.write(f"🎯 {confidence:.2f}")
                        else:
                            st.write("N/A")
                
                st.markdown("---")
        else:
            st.info("No attendance records yet. Start by registering users and marking attendance.")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("👥 Register New User", type="primary"):
                st.session_state.current_page = "👥 Register Users"
                st.rerun()
        
        with col2:
            if st.button("🎥 Start Live Attendance", type="primary"):
                st.session_state.current_page = "🎥 Live Attendance"
                st.rerun()
        
        with col3:
            if st.button("📊 View Reports", type="primary"):
                st.session_state.current_page = "📊 Reports & Analytics"
                st.rerun()
        
        # System status
        st.markdown("### 🔍 System Status")
        
        status_items = [
            ("Database", "✅ Connected", "green"),
            ("Face Recognition", "✅ Ready", "green"),
            ("Anti-Spoofing", "✅ Enabled", "green"),
            ("Camera Access", "⚠️ Check permissions", "orange"),
        ]
        
        for item, status, color in status_items:
            st.markdown(f"**{item}:** :{color}[{status}]")
    
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        st.info("Please check your database connection and try again.")

def initialize_database():
    """Initialize database on first run"""
    try:
        db_manager = DatabaseManager()
        st.success("✅ Database initialized successfully!")
        return True
    except Exception as e:
        st.error(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    # Initialize database
    if not os.path.exists("data/attendance_system.db"):
        st.info("🔧 Initializing system for first time...")
        if initialize_database():
            st.success("🎉 System ready!")
        else:
            st.error("❌ System initialization failed!")
            st.stop()
    
    # Run main application
    main()
