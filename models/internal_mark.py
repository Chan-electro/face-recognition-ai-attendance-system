from datetime import datetime
from models import db


class InternalMark(db.Model):
    """Internal marks/assessment model"""
    
    __tablename__ = 'internal_marks'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)  # 'IA1', 'IA2', 'IA3', 'ASSIGNMENT', 'SEE', etc.
    marks_obtained = db.Column(db.Float, nullable=False)
    max_marks = db.Column(db.Float, default=50.0)
    semester = db.Column(db.Integer, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='internal_marks')
    subject = db.relationship('Subject', backref='internal_marks')
    uploader = db.relationship('User', foreign_keys=[uploaded_by])
    
    def __repr__(self):
        return f'<InternalMark {self.student_id} - {self.subject_id} - {self.exam_type}: {self.marks_obtained}/{self.max_marks}>'
    
    def to_dict(self):
        """Convert internal mark to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.full_name if self.student else None,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'subject_code': self.subject.code if self.subject else None,
            'exam_type': self.exam_type,
            'marks_obtained': self.marks_obtained,
            'max_marks': self.max_marks,
            'percentage': round((self.marks_obtained / self.max_marks) * 100, 2) if self.max_marks else 0,
            'semester': self.semester,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }
