from datetime import datetime, time
from models import db


class Timetable(db.Model):
    """Class timetable/schedule model"""
    
    __tablename__ = 'timetable'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)  # MONDAY, TUESDAY, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.Column(db.String(50), nullable=True)
    semester = db.Column(db.Integer, nullable=True)
    department = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subject = db.relationship('Subject', backref='timetable_entries', lazy=True)
    
    def __repr__(self):
        return f'<Timetable {self.day_of_week} {self.start_time} - {self.subject_id}>'
    
    def to_dict(self):
        """Convert timetable to dictionary"""
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'subject_code': self.subject.code if self.subject else None,
            'faculty_name': self.subject.faculty.name if self.subject and self.subject.faculty else None,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'room': self.room,
            'semester': self.semester,
            'department': self.department,
            'is_active': self.is_active
        }
    
    @staticmethod
    def get_schedule_for_day(day, semester=None, department=None):
        """Get timetable for a specific day"""
        query = Timetable.query.filter_by(day_of_week=day.upper(), is_active=True)
        
        if semester:
            query = query.filter_by(semester=semester)
        if department:
            query = query.filter_by(department=department)
        
        return query.order_by(Timetable.start_time).all()
