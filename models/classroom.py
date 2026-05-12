from datetime import datetime
from models import db


class Classroom(db.Model):
    __tablename__ = 'classrooms'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    semester      = db.Column(db.Integer, nullable=False)
    section       = db.Column(db.String(10), nullable=False)
    department    = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(20), nullable=True)
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    students    = db.relationship('User', backref='classroom', lazy='dynamic',
                                  foreign_keys='User.classroom_id')
    assignments = db.relationship('TeacherAssignment', backref='classroom',
                                  lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':            self.id,
            'name':          self.name,
            'semester':      self.semester,
            'section':       self.section,
            'department':    self.department,
            'academic_year': self.academic_year,
            'is_active':     self.is_active,
        }

    def __repr__(self):
        return f'<Classroom {self.name}>'
