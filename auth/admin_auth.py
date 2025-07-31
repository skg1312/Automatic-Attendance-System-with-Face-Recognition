import streamlit as st
from database.db_manager import DatabaseManager
import hashlib

class AdminAuth:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def login(self, username: str, password: str) -> bool:
        """
        Authenticate admin user
        Args:
            username: Admin username
            password: Admin password
        Returns:
            bool: True if authentication successful
        """
        return self.db_manager.verify_admin(username, password)
    
    def is_logged_in(self) -> bool:
        """Check if admin is logged in"""
        return st.session_state.get('logged_in', False)
    
    def get_current_user(self) -> str:
        """Get current logged in username"""
        return st.session_state.get('username', '')
    
    def logout(self):
        """Logout current user"""
        for key in ['logged_in', 'username']:
            if key in st.session_state:
                del st.session_state[key]
    
    def require_auth(self):
        """Decorator to require authentication"""
        if not self.is_logged_in():
            st.error("Please login to access this page")
            st.stop()
    
    def login_form(self):
        """Display login form"""
        st.title("🔐 Admin Login")
        st.write("Please enter both username and password")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter admin username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if username and password:
                    if self.login(username, password):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")
        
        # Default credentials info - prominently displayed
        st.markdown("---")
        st.subheader("ℹ️ Default Credentials")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("""
            **Default Admin Credentials:**
            - Username: `admin`
            - Password: `admin`
            """)
        with col2:
            st.warning("""
            **Security Note:**
            Please change these credentials after first login for security.
            """)
    
    def logout_button(self):
        """Display logout button in sidebar"""
        if self.is_logged_in():
            st.sidebar.write(f"👤 Logged in as: **{self.get_current_user()}**")
            if st.sidebar.button("🚪 Logout"):
                self.logout()
                st.rerun()
