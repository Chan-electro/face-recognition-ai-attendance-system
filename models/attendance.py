from datetime import datetime
from models import db


class Attendance(db.Model):
    """Attendance record model"""
    
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PRESENT')  # PRESENT, ABSENT, LATE
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Teacher who marked
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    confidence_score = db.Column(db.Float, nullable=True)  # Face recognition confidence
    is_manual = db.Column(db.Boolean, default=False)  # Manual override vs face recognition
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships handled by User model backref
    subject = db.relationship('Subject', backref='attendance_records', lazy=True)
    
    def __repr__(self):
        return f'<Attendance {self.student_id} - {self.subject_id} - {self.date} - {self.status}>'
    
    def to_dict(self):
        """Convert attendance to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.full_name if self.student else None,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time.isoformat() if self.time else None,
            'status': self.status,
            'marked_by': self.marked_by,
            'marked_at': self.marked_at.isoformat() if self.marked_at else None,
            'confidence_score': self.confidence_score,
            'is_manual': self.is_manual,
            'notes': self.notes
        }
    
    @staticmethod
    def get_attendance_percentage(student_id, subject_id=None):
        """Calculate attendance percentage for a student"""
        query = Attendance.query.filter_by(student_id=student_id)
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        
        total = query.count()
        if total == 0:
            return 0.0
        
        present = query.filter(Attendance.status.in_(['PRESENT', 'LATE'])).count()
        return round((present / total) * 100, 2)
