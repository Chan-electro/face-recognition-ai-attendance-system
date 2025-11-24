from datetime import datetime
from models import db


class Subject(db.Model):
    """Subject/Course model"""
    
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    credits = db.Column(db.Integer, nullable=True)
    semester = db.Column(db.Integer, nullable=True)
    department = db.Column(db.String(100), nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    faculty = db.relationship('Faculty', backref='subjects', lazy=True)
    
    def __repr__(self):
        return f'<Subject {self.code} - {self.name}>'
    
    def to_dict(self):
        """Convert subject to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'credits': self.credits,
            'semester': self.semester,
            'department': self.department,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.name if self.faculty else None,
            'is_active': self.is_active
        }
