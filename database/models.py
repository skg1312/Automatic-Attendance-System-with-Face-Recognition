"""
Database Models

This module defines the database schema and models for the attendance system.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any
import sqlite3

@dataclass
class User:
    """User model for registered users"""
    id: Optional[int] = None
    name: str = ""
    employee_id: str = ""
    email: str = ""
    department: str = ""
    face_encoding: Optional[bytes] = None
    image_path: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'employee_id': self.employee_id,
            'email': self.email,
            'department': self.department,
            'face_encoding': self.face_encoding,
            'image_path': self.image_path,
            'created_at': self.created_at
        }

@dataclass
class AttendanceRecord:
    """Attendance record model"""
    id: Optional[int] = None
    user_id: int = 0
    name: str = ""
    employee_id: str = ""
    department: str = ""
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    date: Optional[datetime] = None
    confidence: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert attendance record to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'employee_id': self.employee_id,
            'department': self.department,
            'check_in': self.check_in,
            'check_out': self.check_out,
            'date': self.date,
            'confidence': self.confidence
        }

@dataclass
class Admin:
    """Admin user model"""
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert admin to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'created_at': self.created_at
        }

class DatabaseSchema:
    """Database schema definitions"""
    
    @staticmethod
    def get_create_tables_sql() -> list:
        """Get SQL statements to create all tables"""
        
        users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            employee_id TEXT UNIQUE NOT NULL,
            email TEXT,
            department TEXT,
            face_encoding BLOB,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        attendance_table = """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            department TEXT,
            check_in TIMESTAMP,
            check_out TIMESTAMP,
            date DATE DEFAULT CURRENT_DATE,
            confidence REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
        
        admin_table = """
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        return [users_table, attendance_table, admin_table]
    
    @staticmethod
    def get_indexes_sql() -> list:
        """Get SQL statements to create indexes for better performance"""
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_employee_id ON users(employee_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON attendance(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_employee_id ON attendance(employee_id)",
            "CREATE INDEX IF NOT EXISTS idx_admin_username ON admin_users(username)"
        ]
        
        return indexes
