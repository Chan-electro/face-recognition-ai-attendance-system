from datetime import datetime
from models import db


class Faculty(db.Model):
    """Faculty/Teacher information model"""
    
    __tablename__ = 'faculty'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    designation = db.Column(db.String(100), nullable=True)  # Professor, Assistant Professor, etc.
    department = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    office = db.Column(db.String(50), nullable=True)
    specialization = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships handled by Subject backref
    
    def __repr__(self):
        return f'<Faculty {self.name} - {self.designation}>'
    
    def to_dict(self):
        """Convert faculty to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'designation': self.designation,
            'department': self.department,
            'email': self.email,
            'phone': self.phone,
            'office': self.office,
            'specialization': self.specialization,
            'is_active': self.is_active
        }
