from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(db.Model):
    """User model for students, teachers, and admins"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # STUDENT, TEACHER, ADMIN
    student_id = db.Column(db.String(20), unique=True, nullable=True)  # For students only
    department = db.Column(db.String(100), nullable=True)
    semester = db.Column(db.Integer, nullable=True)  # For students
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    attendance_records = db.relationship('Attendance', backref='student', lazy='dynamic', 
                                        foreign_keys='Attendance.student_id')
    face_encodings = db.relationship('FaceEncoding', backref='user', lazy='dynamic', 
                                     cascade='all, delete-orphan')
    marked_attendance = db.relationship('Attendance', backref='marker', lazy='dynamic',
                                       foreign_keys='Attendance.marked_by')
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'student_id': self.student_id,
            'department': self.department,
            'semester': self.semester,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def is_student(self):
        return self.role == 'STUDENT'
    
    @property
    def is_teacher(self):
        return self.role == 'TEACHER'
    
    @property
    def is_admin(self):
        return self.role == 'ADMIN'
