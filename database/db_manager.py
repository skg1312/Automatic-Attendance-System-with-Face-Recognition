import sqlite3
import os
from datetime import datetime
import bcrypt
import pickle

class DatabaseManager:
    def __init__(self, db_path="data/attendance_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection with datetime parsing"""
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        return conn
    
    def init_database(self):
        """Initialize database with required tables"""
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create admin table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create users table (students/employees)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                employee_id TEXT UNIQUE NOT NULL,
                email TEXT,
                department TEXT,
                face_encoding BLOB,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                check_in_time TIMESTAMP,
                check_out_time TIMESTAMP,
                date DATE,
                status TEXT DEFAULT 'present',
                confidence_score REAL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create attendance log table for detailed logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT,
                confidence_score REAL,
                image_path TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create default admin if not exists
        self.create_default_admin()
        
        conn.commit()
        conn.close()
    
    def create_default_admin(self):
        """Create default admin account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if admin exists
        cursor.execute("SELECT id FROM admins WHERE username = ?", ("admin",))
        if not cursor.fetchone():
            # Create default admin with password 'admin'
            password_hash = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                ("admin", password_hash)
            )
            conn.commit()
        
        conn.close()
    
    def verify_admin(self, username, password):
        """Verify admin credentials"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash FROM admins WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return bcrypt.checkpw(password.encode('utf-8'), result[0])
        return False
    
    def add_user(self, name, employee_id, email, department, face_encoding, image_path):
        """Add new user to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Serialize face encoding
            face_encoding_blob = pickle.dumps(face_encoding)
            
            cursor.execute('''
                INSERT INTO users (name, employee_id, email, department, face_encoding, image_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, employee_id, email, department, face_encoding_blob, image_path))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def get_all_users(self):
        """Get all active users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, employee_id, email, department, image_path, created_at
            FROM users 
            WHERE is_active = 1
            ORDER BY name
        ''')
        
        users = cursor.fetchall()
        conn.close()
        return users
    
    def get_user_face_encodings(self):
        """Get all user face encodings for recognition"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, employee_id, face_encoding
            FROM users 
            WHERE is_active = 1 AND face_encoding IS NOT NULL
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        encodings = []
        for user_id, name, employee_id, face_encoding_blob in results:
            if face_encoding_blob:
                face_encoding = pickle.loads(face_encoding_blob)
                encodings.append({
                    'id': user_id,
                    'name': name,
                    'employee_id': employee_id,
                    'encoding': face_encoding
                })
        
        return encodings
    
    def mark_attendance(self, user_id, confidence_score, action='check_in'):
        """Mark attendance for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        current_time = datetime.now()
        
        # Check if user already has attendance for today
        cursor.execute('''
            SELECT id, check_in_time, check_out_time FROM attendance 
            WHERE user_id = ? AND date = ?
        ''', (user_id, today))
        
        existing_record = cursor.fetchone()
        
        if existing_record:
            # Update existing record
            record_id, check_in_time, check_out_time = existing_record
            
            if action == 'check_out' and check_in_time and not check_out_time:
                # Mark check out
                cursor.execute('''
                    UPDATE attendance 
                    SET check_out_time = ?, confidence_score = ?
                    WHERE id = ?
                ''', (current_time, confidence_score, record_id))
            elif action == 'check_in' and not check_in_time:
                # Update check in
                cursor.execute('''
                    UPDATE attendance 
                    SET check_in_time = ?, confidence_score = ?
                    WHERE id = ?
                ''', (current_time, confidence_score, record_id))
        else:
            # Create new attendance record
            if action == 'check_in':
                cursor.execute('''
                    INSERT INTO attendance (user_id, check_in_time, date, confidence_score)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, current_time, today, confidence_score))
        
        # Add to attendance log
        cursor.execute('''
            INSERT INTO attendance_logs (user_id, action, confidence_score)
            VALUES (?, ?, ?)
        ''', (user_id, action, confidence_score))
        
        conn.commit()
        conn.close()
        return True
    
    def get_attendance_records(self, date=None, user_id=None):
        """Get attendance records"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT a.id, u.name, u.employee_id, u.department,
                   a.check_in_time, a.check_out_time, a.date, a.confidence_score
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE 1=1
        '''
        params = []
        
        if date:
            query += " AND a.date = ?"
            params.append(date)
        
        if user_id:
            query += " AND a.user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY a.date DESC, a.check_in_time DESC"
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        conn.close()
        
        return records
    
    def get_attendance_summary(self, start_date=None, end_date=None):
        """Get attendance summary statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                COUNT(DISTINCT a.user_id) as total_users,
                COUNT(a.id) as total_attendance_records,
                COUNT(CASE WHEN a.check_in_time IS NOT NULL THEN 1 END) as check_ins,
                COUNT(CASE WHEN a.check_out_time IS NOT NULL THEN 1 END) as check_outs
            FROM attendance a
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += " AND a.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND a.date <= ?"
            params.append(end_date)
        
        cursor.execute(query, params)
        summary = cursor.fetchone()
        conn.close()
        
        return summary
    
    def delete_user(self, user_id):
        """Soft delete user (mark as inactive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
