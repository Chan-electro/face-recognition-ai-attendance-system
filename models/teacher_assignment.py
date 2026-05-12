from models import db


class TeacherAssignment(db.Model):
    __tablename__ = 'teacher_assignments'
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'classroom_id', 'subject_id',
                            name='uq_teacher_classroom_subject'),
    )

    id           = db.Column(db.Integer, primary_key=True)
    teacher_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False, index=True)
    subject_id   = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)

    teacher = db.relationship('User', foreign_keys=[teacher_id],
                              backref=db.backref('assignments', lazy='dynamic'))
    subject = db.relationship('Subject', backref='teacher_assignments')

    def to_dict(self):
        return {
            'id':           self.id,
            'teacher_id':   self.teacher_id,
            'teacher_name': self.teacher.full_name if self.teacher else None,
            'classroom_id': self.classroom_id,
            'subject_id':   self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'subject_code': self.subject.code if self.subject else None,
        }

    def __repr__(self):
        return f'<TeacherAssignment teacher={self.teacher_id} classroom={self.classroom_id} subject={self.subject_id}>'
