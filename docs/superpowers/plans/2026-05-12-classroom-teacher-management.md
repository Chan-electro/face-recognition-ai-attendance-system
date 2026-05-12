# Classroom & Teacher Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add proper classroom entities, per-classroom teacher–subject assignments, a classroom-scoped teacher dashboard with a header dropdown switcher, and 30-day seeded attendance data for 60 demo students.

**Architecture:** Two new SQLAlchemy models (`Classroom`, `TeacherAssignment`) join the existing `User`/`Subject` tables. A `classroom_id` FK is added to `users` for students. Teacher controller routes read `session['active_classroom_id']` to scope all queries; a `/teacher/switch-classroom` endpoint updates that key. Admin gets two new pages (classroom list, classroom detail) and teacher/student forms gain classroom-aware fields.

**Tech Stack:** Flask, SQLAlchemy, Jinja2, Tailwind CSS (CDN), Lucide icons, SQLite.

---

## File Map

| Action | File |
|--------|------|
| Create | `models/classroom.py` |
| Create | `models/teacher_assignment.py` |
| Create | `templates/admin/manage_classrooms.html` |
| Create | `templates/admin/classroom_detail.html` |
| Modify | `models/__init__.py` |
| Modify | `app.py` |
| Modify | `utils/db_utils.py` |
| Modify | `controllers/admin_controller.py` |
| Modify | `controllers/teacher_controller.py` |
| Modify | `templates/base.html` |
| Modify | `templates/admin/manage_users.html` |
| Modify | `templates/teacher/dashboard.html` |
| Modify | `templates/teacher/mark_attendance.html` |
| Modify | `templates/teacher/view_students.html` |
| Modify | `templates/teacher/class_attendance.html` |
| Modify | `templates/teacher/enter_marks.html` |

---

## Task 1: Classroom model

**Files:**
- Create: `models/classroom.py`

- [ ] **Step 1: Create the file**

```python
# models/classroom.py
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

    students     = db.relationship('User', backref='classroom', lazy='dynamic',
                                   foreign_keys='User.classroom_id')
    assignments  = db.relationship('TeacherAssignment', backref='classroom',
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
```

- [ ] **Step 2: Commit**

```bash
git add models/classroom.py
git commit -m "feat: add Classroom model"
```

---

## Task 2: TeacherAssignment model

**Files:**
- Create: `models/teacher_assignment.py`

- [ ] **Step 1: Create the file**

```python
# models/teacher_assignment.py
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

    teacher  = db.relationship('User', foreign_keys=[teacher_id],
                               backref=db.backref('assignments', lazy='dynamic'))
    subject  = db.relationship('Subject', backref='teacher_assignments')

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
```

- [ ] **Step 2: Commit**

```bash
git add models/teacher_assignment.py
git commit -m "feat: add TeacherAssignment model"
```

---

## Task 3: Register new models and add DB migration

**Files:**
- Modify: `models/__init__.py`
- Modify: `app.py`

- [ ] **Step 1: Add imports to `models/__init__.py`**

Replace the last two lines of the file with:

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models for easy access
from models.user import User
from models.attendance import Attendance
from models.face_encoding import FaceEncoding
from models.subject import Subject
from models.faculty import Faculty
from models.timetable import Timetable
from models.internal_mark import InternalMark
from models.note import Note
from models.classroom import Classroom
from models.teacher_assignment import TeacherAssignment
```

- [ ] **Step 2: Add `User.classroom_id` FK and inline migration to `app.py`**

Inside `create_app()`, after the existing `section` migration block (around line 52), add:

```python
        # Migrate: add 'classroom_id' column to users if missing
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result]
                if 'classroom_id' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN classroom_id INTEGER REFERENCES classrooms(id)"))
                    conn.commit()
                    print("Migration: added 'classroom_id' column to users table")
        except Exception as e:
            print(f"Migration check (classroom_id): {e}")
```

Also add `classroom_id` to the `User` model in `models/user.py` after the `section` column:

```python
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True, index=True)
```

- [ ] **Step 3: Commit**

```bash
git add models/__init__.py app.py models/user.py
git commit -m "feat: register Classroom/TeacherAssignment models and add classroom_id migration"
```

---

## Task 4: Rewrite seed_database with classrooms, 60 students, and 30-day attendance

**Files:**
- Modify: `utils/db_utils.py`

- [ ] **Step 1: Replace `seed_database()` with the new implementation**

```python
import random
from datetime import datetime, date, timedelta


def seed_database(app):
    """Seed database with initial data including classrooms and attendance history."""
    with app.app_context():
        from models.user import User
        if User.query.first():
            print("Database already contains data. Skipping seed.")
            return

        print("Seeding database...")
        from models import db
        from models.user import User
        from models.faculty import Faculty
        from models.subject import Subject
        from models.timetable import Timetable
        from models.classroom import Classroom
        from models.teacher_assignment import TeacherAssignment
        from models.attendance import Attendance

        # ── Admin ────────────────────────────────────────────
        admin = User(username='admin', email='admin@college.edu',
                     full_name='System Administrator', role='ADMIN',
                     department='Administration')
        admin.set_password('admin123')
        db.session.add(admin)

        # ── Teachers ─────────────────────────────────────────
        teacher1 = User(username='teacher1', email='rajesh.kumar@college.edu',
                        full_name='Dr. Rajesh Kumar', role='TEACHER',
                        department='Computer Science')
        teacher1.set_password('teacher123')
        db.session.add(teacher1)

        teacher2 = User(username='teacher2', email='anjali.sharma@college.edu',
                        full_name='Prof. Anjali Sharma', role='TEACHER',
                        department='Computer Science')
        teacher2.set_password('teacher123')
        db.session.add(teacher2)
        db.session.commit()

        # ── Classrooms ───────────────────────────────────────
        cls_a = Classroom(name='CSE 8th Sem A', semester=8, section='A',
                          department='Computer Science', academic_year='2025-26')
        cls_b = Classroom(name='CSE 8th Sem B', semester=8, section='B',
                          department='Computer Science', academic_year='2025-26')
        db.session.add_all([cls_a, cls_b])
        db.session.commit()

        # ── Faculty ──────────────────────────────────────────
        faculty_data = [
            ('Dr. Rajesh Kumar', 'Professor', 'Computer Science',
             'rajesh.kumar@college.edu', '9876543210', 'CS-301', 'Data Structures, Algorithms'),
            ('Prof. Anjali Sharma', 'Assistant Professor', 'Computer Science',
             'anjali.sharma@college.edu', '9876543211', 'CS-302', 'Operating Systems, Computer Networks'),
            ('Dr. Vikram Singh', 'Associate Professor', 'Computer Science',
             'vikram.singh@college.edu', '9876543212', 'CS-303', 'Database Management, Software Engineering'),
            ('Prof. Meera Nair', 'Assistant Professor', 'Computer Science',
             'meera.nair@college.edu', '9876543213', 'CS-304', 'Web Technologies, Mobile Computing'),
            ('Dr. Sanjay Gupta', 'Professor', 'Computer Science',
             'sanjay.gupta@college.edu', '9876543214', 'CS-305', 'Artificial Intelligence, Machine Learning'),
        ]
        faculty_objects = []
        for name, desig, dept, email, phone, office, spec in faculty_data:
            from models.faculty import Faculty
            f = Faculty(name=name, designation=desig, department=dept, email=email,
                        phone=phone, office=office, specialization=spec)
            db.session.add(f)
            faculty_objects.append(f)
        db.session.commit()

        # ── Subjects ─────────────────────────────────────────
        subjects_data = [
            ('CS501', 'Data Structures and Algorithms',
             'Advanced data structures and algorithm design', 4, 5, 0),
            ('CS502', 'Operating Systems',
             'Process management, memory management, file systems', 4, 5, 1),
            ('CS503', 'Database Management Systems',
             'Relational databases, SQL, normalization', 4, 5, 2),
            ('CS504', 'Web Technologies',
             'HTML, CSS, JavaScript, Flask, React', 3, 5, 3),
            ('CS505', 'Computer Networks',
             'Network protocols, TCP/IP, network security', 4, 5, 1),
            ('CS506', 'Artificial Intelligence',
             'Search algorithms, logic, machine learning basics', 3, 5, 4),
            ('CS507', 'Software Engineering',
             'SDLC, agile methodologies, testing', 3, 5, 2),
        ]
        subject_objects = []
        for code, name, desc, credits, sem, fac_idx in subjects_data:
            s = Subject(code=code, name=name, description=desc, credits=credits,
                        semester=sem, department='Computer Science',
                        faculty_id=faculty_objects[fac_idx].id)
            db.session.add(s)
            subject_objects.append(s)
        db.session.commit()

        # subject shorthand
        s501, s502, s503, s504, s505 = (subject_objects[i] for i in range(5))

        # ── Teacher Assignments ───────────────────────────────
        assignments = [
            TeacherAssignment(teacher_id=teacher1.id, classroom_id=cls_a.id, subject_id=s501.id),
            TeacherAssignment(teacher_id=teacher1.id, classroom_id=cls_a.id, subject_id=s502.id),
            TeacherAssignment(teacher_id=teacher1.id, classroom_id=cls_b.id, subject_id=s503.id),
            TeacherAssignment(teacher_id=teacher2.id, classroom_id=cls_a.id, subject_id=s503.id),
            TeacherAssignment(teacher_id=teacher2.id, classroom_id=cls_b.id, subject_id=s504.id),
            TeacherAssignment(teacher_id=teacher2.id, classroom_id=cls_b.id, subject_id=s505.id),
        ]
        db.session.add_all(assignments)
        db.session.commit()

        # ── Timetable ─────────────────────────────────────────
        from datetime import time as dtime
        timetable_data = [
            (0, 'MONDAY', dtime(9, 0), dtime(10, 0), 'Room 101'),
            (1, 'MONDAY', dtime(10, 0), dtime(11, 0), 'Room 102'),
            (2, 'MONDAY', dtime(11, 30), dtime(12, 30), 'Room 103'),
            (3, 'TUESDAY', dtime(9, 0), dtime(10, 0), 'Room 101'),
            (4, 'TUESDAY', dtime(10, 0), dtime(11, 0), 'Room 102'),
            (0, 'WEDNESDAY', dtime(9, 0), dtime(10, 0), 'Room 101'),
            (2, 'WEDNESDAY', dtime(10, 0), dtime(11, 0), 'Room 103'),
            (1, 'THURSDAY', dtime(9, 0), dtime(10, 0), 'Room 102'),
            (4, 'FRIDAY', dtime(9, 0), dtime(10, 0), 'Room 102'),
        ]
        for subj_idx, day, start, end, room in timetable_data:
            entry = Timetable(subject_id=subject_objects[subj_idx].id,
                              day_of_week=day, start_time=start, end_time=end,
                              room=room, semester=5, department='Computer Science')
            db.session.add(entry)
        db.session.commit()

        # ── Students (60 total, 30 per classroom) ────────────
        all_students = []
        random.seed(42)

        # Decide attendance tier per student index deterministically
        # 0-35 (60%): good (75-92%), 36-50 (25%): at-risk (55-74%), 51-59 (15%): excellent (93-100%)
        def presence_rate(idx):
            if idx < 36:
                return random.uniform(0.75, 0.92)
            elif idx < 51:
                return random.uniform(0.55, 0.74)
            else:
                return random.uniform(0.93, 1.00)

        for i in range(60):
            n = i + 1
            cls = cls_a if i < 30 else cls_b
            sec = 'A' if i < 30 else 'B'
            student = User(
                username=f'student{n}',
                email=f'student{n}@student.college.edu',
                full_name=_student_name(i),
                role='STUDENT',
                student_id=f'CS{n:03d}',
                department='Computer Science',
                semester=8,
                section=sec,
                classroom_id=cls.id,
            )
            student.set_password('student123')
            db.session.add(student)
            all_students.append((student, presence_rate(i)))

        db.session.commit()

        # ── 30-day attendance history ─────────────────────────
        today = date.today()
        # Subjects taught in each classroom (derived from assignments above)
        cls_a_subjects = [s501, s502, s503]
        cls_b_subjects = [s503, s504, s505]

        attendance_records = []
        for student, rate in all_students:
            subjects = cls_a_subjects if student.section == 'A' else cls_b_subjects
            for subject in subjects:
                for day_offset in range(30):
                    att_date = today - timedelta(days=day_offset + 1)
                    if att_date.weekday() >= 5:   # skip weekends
                        continue
                    status = 'PRESENT' if random.random() < rate else 'ABSENT'
                    attendance_records.append(Attendance(
                        student_id=student.id,
                        subject_id=subject.id,
                        date=att_date,
                        time=dtime(9, 0),
                        status=status,
                        is_manual=True,
                    ))

        # Bulk insert in chunks of 500 to avoid SQLite limits
        chunk = 500
        for start in range(0, len(attendance_records), chunk):
            db.session.add_all(attendance_records[start:start + chunk])
            db.session.commit()

        print(f"Seeded {len(all_students)} students, {len(attendance_records)} attendance records.")
        print("\nDefault credentials — Admin: admin/admin123 | Teacher: teacher1/teacher123 | Student: student1/student123\n")


def _student_name(idx):
    """Return a plausible Indian name for the given zero-based student index."""
    first = [
        'Rahul','Priya','Amit','Sneha','Vikram','Ananya','Rohan','Kavita','Arjun','Megha',
        'Karan','Divya','Siddharth','Pooja','Aditya','Riya','Nikhil','Shruti','Varun','Neha',
        'Deepak','Ankita','Rajat','Swati','Harsh','Preeti','Mohit','Kajal','Sachin','Shweta',
        'Aman','Simran','Gaurav','Nisha','Vivek','Tanvi','Aakash','Pallavi','Pranav','Juhi',
        'Suresh','Meena','Vishal','Sonal','Tarun','Bhavna','Manish','Rekha','Hemant','Usha',
        'Lalit','Geeta','Naveen','Sunita','Rohit','Madhu','Ajay','Sita','Ankit','Gita',
    ]
    last = [
        'Verma','Singh','Patel','Reddy','Sharma','Gupta','Das','Iyer','Nair','Kapoor',
        'Kumar','Mishra','Joshi','Shah','Yadav','Tiwari','Rao','Pillai','Menon','Chauhan',
        'Bose','Ghosh','Chatterjee','Mukherjee','Sen','Roy','Dey','Saha','Paul','Biswas',
        'Desai','Mehta','Gandhi','Modi','Trivedi','Pandya','Bhatt','Jain','Agarwal','Bansal',
        'Malhotra','Khanna','Bhatia','Arora','Sethi','Luthra','Chopra','Tandon','Grover','Anand',
        'Saxena','Srivastava','Dubey','Awasthi','Tripathi','Shukla','Tiwari','Upadhyay','Bajpai','Misra',
    ]
    return f"{first[idx % len(first)]} {last[idx % len(last)]}"
```

- [ ] **Step 2: Start the app to verify seed runs without error**

```bash
rm -f database/attendance.db
python app.py &
sleep 5
curl -s http://localhost:5000/login | grep -c "Login"
kill %1
```

Expected: prints a number > 0 (login page is reachable) and no traceback in stdout.

- [ ] **Step 3: Commit**

```bash
git add utils/db_utils.py
git commit -m "feat: rewrite seed_database with classrooms, 60 students, and 30-day attendance"
```

---

## Task 5: Admin — classroom CRUD routes

**Files:**
- Modify: `controllers/admin_controller.py`

- [ ] **Step 1: Add classroom list + create + delete endpoints**

Append to the bottom of `controllers/admin_controller.py`:

```python
# ─── Classroom management ────────────────────────────────────────────────────

@admin_bp.route('/classrooms')
@role_required('ADMIN')
def manage_classrooms():
    from models.classroom import Classroom
    from models.teacher_assignment import TeacherAssignment
    user = User.query.get(session.get('user_id'))
    classrooms = Classroom.query.order_by(Classroom.semester, Classroom.section).all()
    classroom_data = []
    for c in classrooms:
        teacher_count = db.session.query(
            db.func.count(db.func.distinct(TeacherAssignment.teacher_id))
        ).filter_by(classroom_id=c.id).scalar() or 0
        classroom_data.append({
            'classroom': c,
            'student_count': c.students.filter_by(is_active=True).count(),
            'teacher_count': teacher_count,
        })
    return render_template('admin/manage_classrooms.html',
                           user=user, classroom_data=classroom_data)


@admin_bp.route('/classrooms/add', methods=['POST'])
@role_required('ADMIN')
def add_classroom():
    from models.classroom import Classroom
    try:
        data = request.get_json() if request.is_json else request.form
        name          = str(data.get('name', '')).strip()
        semester      = data.get('semester')
        section       = str(data.get('section', '')).strip().upper()
        department    = str(data.get('department', '')).strip()
        academic_year = str(data.get('academic_year', '')).strip()

        if not all([name, semester, section, department]):
            return jsonify({'success': False, 'message': 'Name, semester, section and department are required'}), 400

        cls = Classroom(name=name, semester=int(semester), section=section,
                        department=department, academic_year=academic_year or None)
        db.session.add(cls)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Classroom "{name}" created', 'classroom': cls.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/classrooms/<int:cls_id>/delete', methods=['POST'])
@role_required('ADMIN')
def delete_classroom(cls_id):
    from models.classroom import Classroom
    try:
        cls = Classroom.query.get(cls_id)
        if not cls:
            return jsonify({'success': False, 'message': 'Classroom not found'}), 404
        cls.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': f'Classroom "{cls.name}" deactivated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
```

- [ ] **Step 2: Commit**

```bash
git add controllers/admin_controller.py
git commit -m "feat: add classroom CRUD admin routes"
```

---

## Task 6: Admin — classroom detail routes (students + assignments)

**Files:**
- Modify: `controllers/admin_controller.py`

- [ ] **Step 1: Add classroom detail, student add/remove, and assignment add/delete endpoints**

Append to `controllers/admin_controller.py`:

```python
@admin_bp.route('/classrooms/<int:cls_id>')
@role_required('ADMIN')
def classroom_detail(cls_id):
    from models.classroom import Classroom
    from models.teacher_assignment import TeacherAssignment
    user = User.query.get(session.get('user_id'))
    cls = Classroom.query.get_or_404(cls_id)
    students      = cls.students.filter_by(is_active=True).order_by(User.full_name).all()
    unassigned    = User.query.filter_by(role='STUDENT', is_active=True, classroom_id=None).order_by(User.full_name).all()
    assignments   = TeacherAssignment.query.filter_by(classroom_id=cls_id).all()
    teachers      = User.query.filter_by(role='TEACHER', is_active=True).order_by(User.full_name).all()
    subjects      = Subject.query.filter_by(is_active=True).order_by(Subject.code).all()
    return render_template('admin/classroom_detail.html',
                           user=user, cls=cls, students=students,
                           unassigned=unassigned, assignments=assignments,
                           teachers=teachers, subjects=subjects)


@admin_bp.route('/classrooms/<int:cls_id>/add-student', methods=['POST'])
@role_required('ADMIN')
def classroom_add_student(cls_id):
    from models.classroom import Classroom
    try:
        data       = request.get_json()
        student_id = data.get('student_id')
        student    = User.query.filter_by(id=student_id, role='STUDENT', is_active=True).first()
        cls        = Classroom.query.get(cls_id)
        if not student or not cls:
            return jsonify({'success': False, 'message': 'Student or classroom not found'}), 404
        student.classroom_id = cls_id
        student.semester     = cls.semester
        student.section      = cls.section
        db.session.commit()
        return jsonify({'success': True,
                        'message': f'{student.full_name} added to {cls.name}',
                        'student': student.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/classrooms/<int:cls_id>/remove-student', methods=['POST'])
@role_required('ADMIN')
def classroom_remove_student(cls_id):
    try:
        data       = request.get_json()
        student_id = data.get('student_id')
        student    = User.query.filter_by(id=student_id, role='STUDENT').first()
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        student.classroom_id = None
        db.session.commit()
        return jsonify({'success': True, 'message': f'{student.full_name} removed from classroom'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/classrooms/<int:cls_id>/add-assignment', methods=['POST'])
@role_required('ADMIN')
def classroom_add_assignment(cls_id):
    from models.teacher_assignment import TeacherAssignment
    try:
        data       = request.get_json()
        teacher_id = int(data.get('teacher_id'))
        subject_id = int(data.get('subject_id'))
        existing   = TeacherAssignment.query.filter_by(
            teacher_id=teacher_id, classroom_id=cls_id, subject_id=subject_id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Assignment already exists'}), 400
        ta = TeacherAssignment(teacher_id=teacher_id, classroom_id=cls_id, subject_id=subject_id)
        db.session.add(ta)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Assignment added', 'assignment': ta.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/classrooms/assignments/<int:assignment_id>/delete', methods=['POST'])
@role_required('ADMIN')
def delete_assignment(assignment_id):
    from models.teacher_assignment import TeacherAssignment
    try:
        ta = TeacherAssignment.query.get(assignment_id)
        if not ta:
            return jsonify({'success': False, 'message': 'Assignment not found'}), 404
        db.session.delete(ta)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Assignment removed'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
```

- [ ] **Step 2: Update `add_user` to accept `classroom_id` for students**

In the existing `add_user` function, after the line `semester=semester if role.upper() == 'STUDENT' else None,`, add:

```python
            classroom_id=int(data.get('classroom_id')) if role.upper() == 'STUDENT' and data.get('classroom_id') else None,
```

And after `db.session.commit()` in `add_user`, add sync of semester/section from classroom if provided:

```python
        if new_user.role == 'STUDENT' and new_user.classroom_id:
            from models.classroom import Classroom
            cls = Classroom.query.get(new_user.classroom_id)
            if cls:
                new_user.semester = cls.semester
                new_user.section  = cls.section
                db.session.commit()
```

- [ ] **Step 3: Commit**

```bash
git add controllers/admin_controller.py
git commit -m "feat: add classroom detail routes (students + teacher assignments)"
```

---

## Task 7: Teacher — classroom context helper and switch endpoint

**Files:**
- Modify: `controllers/teacher_controller.py`

- [ ] **Step 1: Add `_get_active_classroom` helper and `/switch-classroom` endpoint at the top of the file, after the imports**

```python
# ── Classroom context helpers ───────────────────────────────────────────────

def _get_teacher_classrooms(teacher_id):
    """Return distinct Classroom objects assigned to this teacher."""
    from models.teacher_assignment import TeacherAssignment
    from models.classroom import Classroom
    rows = (db.session.query(Classroom)
            .join(TeacherAssignment, TeacherAssignment.classroom_id == Classroom.id)
            .filter(TeacherAssignment.teacher_id == teacher_id, Classroom.is_active == True)
            .distinct()
            .order_by(Classroom.name)
            .all())
    return rows


def _get_active_classroom(teacher_id):
    """
    Return the active Classroom for this teacher session.
    Falls back to first assigned classroom; returns None if no assignments exist.
    """
    from models.classroom import Classroom
    classrooms = _get_teacher_classrooms(teacher_id)
    if not classrooms:
        return None
    active_id = session.get('active_classroom_id')
    if active_id:
        match = next((c for c in classrooms if c.id == active_id), None)
        if match:
            return match
    # default to first
    session['active_classroom_id'] = classrooms[0].id
    return classrooms[0]


def _get_classroom_subjects(teacher_id, classroom_id):
    """Return Subject objects this teacher teaches in the given classroom."""
    from models.teacher_assignment import TeacherAssignment
    rows = (TeacherAssignment.query
            .filter_by(teacher_id=teacher_id, classroom_id=classroom_id)
            .all())
    return [r.subject for r in rows]
```

Then add the switch endpoint (after the helper functions, before `dashboard`):

```python
@teacher_bp.route('/switch-classroom', methods=['POST'])
@role_required('TEACHER')
def switch_classroom():
    from models.classroom import Classroom
    teacher_id = session.get('user_id')
    cls_id = request.form.get('classroom_id', type=int)
    classrooms = _get_teacher_classrooms(teacher_id)
    if cls_id and any(c.id == cls_id for c in classrooms):
        session['active_classroom_id'] = cls_id
    return redirect(request.referrer or url_for('teacher.dashboard'))
```

- [ ] **Step 2: Commit**

```bash
git add controllers/teacher_controller.py
git commit -m "feat: add classroom context helpers and switch-classroom endpoint"
```

---

## Task 8: Scope all teacher routes to active classroom

**Files:**
- Modify: `controllers/teacher_controller.py`

- [ ] **Step 1: Rewrite `dashboard` route**

Replace the existing `dashboard()` function with:

```python
@teacher_bp.route('/dashboard')
@role_required('TEACHER')
def dashboard():
    teacher_id  = session.get('user_id')
    user        = User.query.get(teacher_id)
    classrooms  = _get_teacher_classrooms(teacher_id)
    active_cls  = _get_active_classroom(teacher_id)

    if not active_cls:
        return render_template('teacher/dashboard.html',
                               user=user, classrooms=classrooms,
                               active_cls=None, subjects=[],
                               marked_today=0, total_students=0, at_risk=0)

    subjects = _get_classroom_subjects(teacher_id, active_cls.id)
    today    = date.today()

    marked_today   = Attendance.query.filter_by(marked_by=teacher_id, date=today).count()
    total_students = active_cls.students.filter_by(is_active=True).count()

    # at-risk: students below 75% in any subject taught in this classroom
    from services.attendance_service import AttendanceService
    at_risk = 0
    for student in active_cls.students.filter_by(is_active=True).all():
        stats = AttendanceService.get_attendance_stats(student.id)
        if stats['total'] > 0 and stats['percentage'] < 75:
            at_risk += 1

    return render_template('teacher/dashboard.html',
                           user=user, classrooms=classrooms, active_cls=active_cls,
                           subjects=subjects, marked_today=marked_today,
                           total_students=total_students, at_risk=at_risk)
```

- [ ] **Step 2: Rewrite `mark_attendance_page` and `mark_attendance` routes**

Replace the two existing functions with:

```python
@teacher_bp.route('/mark-attendance', methods=['GET'])
@role_required('TEACHER')
def mark_attendance_page():
    teacher_id  = session.get('user_id')
    user        = User.query.get(teacher_id)
    active_cls  = _get_active_classroom(teacher_id)
    classrooms  = _get_teacher_classrooms(teacher_id)

    if not active_cls:
        subjects = []
        students = []
    else:
        subjects = _get_classroom_subjects(teacher_id, active_cls.id)
        students = active_cls.students.filter_by(is_active=True).order_by(User.full_name).all()

    return render_template('teacher/mark_attendance.html',
                           user=user, classrooms=classrooms, active_cls=active_cls,
                           subjects=subjects, students=students)


@teacher_bp.route('/mark-attendance', methods=['POST'])
@role_required('TEACHER')
def mark_attendance():
    try:
        data       = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        student_id = data.get('student_id')
        subject_id = data.get('subject_id')
        status     = data.get('status', 'PRESENT')
        if not student_id or not subject_id:
            return jsonify({'success': False, 'message': 'Missing student or subject'}), 400
        attendance = AttendanceService.mark_attendance(
            student_id=student_id, subject_id=subject_id, status=status,
            marked_by=session.get('user_id'), confidence_score=1.0, is_manual=True)
        if attendance:
            student = User.query.get(student_id)
            return jsonify({'success': True,
                            'message': f'Attendance marked {status} for {student.full_name}',
                            'student_name': student.full_name})
        return jsonify({'success': False, 'message': 'Failed to mark attendance'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
```

- [ ] **Step 3: Rewrite `view_students` route**

Replace the existing function with:

```python
@teacher_bp.route('/students')
@role_required('TEACHER')
def view_students():
    teacher_id = session.get('user_id')
    user       = User.query.get(teacher_id)
    classrooms = _get_teacher_classrooms(teacher_id)
    active_cls = _get_active_classroom(teacher_id)

    students = (active_cls.students.filter_by(is_active=True).order_by(User.full_name).all()
                if active_cls else [])

    student_data = []
    for student in students:
        stats = AttendanceService.get_attendance_stats(student.id)
        student_data.append({'student': student, 'stats': stats})

    return render_template('teacher/view_students.html',
                           user=user, classrooms=classrooms, active_cls=active_cls,
                           student_data=student_data, total_students=len(student_data))
```

- [ ] **Step 4: Rewrite `class_attendance` route**

Replace the existing function with:

```python
@teacher_bp.route('/class-attendance')
@role_required('TEACHER')
def class_attendance():
    teacher_id = session.get('user_id')
    user       = User.query.get(teacher_id)
    classrooms = _get_teacher_classrooms(teacher_id)
    active_cls = _get_active_classroom(teacher_id)

    subject_id  = request.args.get('subject_id', type=int)
    date_str    = request.args.get('date')
    attendance_date = (datetime.strptime(date_str, '%Y-%m-%d').date()
                       if date_str else date.today())

    subjects = _get_classroom_subjects(teacher_id, active_cls.id) if active_cls else []

    if subject_id and active_cls:
        # Only show students in active classroom
        class_records = AttendanceService.get_class_attendance(subject_id, attendance_date)
        cls_student_ids = {s.id for s in active_cls.students.filter_by(is_active=True).all()}
        records = [r for r in class_records if r['student_id'] in cls_student_ids]
        selected_subject = Subject.query.get(subject_id)
    else:
        records = []
        selected_subject = None

    return render_template('teacher/class_attendance.html',
                           user=user, classrooms=classrooms, active_cls=active_cls,
                           subjects=subjects, selected_subject=selected_subject,
                           attendance_date=attendance_date, records=records)
```

- [ ] **Step 5: Rewrite `enter_marks_page` and `enter_marks` routes**

Replace the two existing functions with:

```python
@teacher_bp.route('/enter-marks', methods=['GET'])
@role_required('TEACHER')
def enter_marks_page():
    teacher_id = session.get('user_id')
    user       = User.query.get(teacher_id)
    classrooms = _get_teacher_classrooms(teacher_id)
    active_cls = _get_active_classroom(teacher_id)

    subjects = _get_classroom_subjects(teacher_id, active_cls.id) if active_cls else []
    students = (active_cls.students.filter_by(is_active=True).order_by(User.full_name).all()
                if active_cls else [])

    return render_template('teacher/enter_marks.html',
                           user=user, classrooms=classrooms, active_cls=active_cls,
                           subjects=subjects, students=students,
                           exam_types=['IA1', 'IA2', 'IA3', 'ASSIGNMENT', 'SEE'])


@teacher_bp.route('/enter-marks', methods=['POST'])
@role_required('TEACHER')
def enter_marks():
    try:
        data       = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        student_id = data.get('student_id')
        subject_id = data.get('subject_id')
        exam_type  = data.get('exam_type')
        marks      = data.get('marks')
        max_marks  = data.get('max_marks', 50.0)
        if not all([student_id, subject_id, exam_type, marks is not None]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        try:
            marks     = float(marks)
            max_marks = float(max_marks)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid mark value'}), 400
        existing = InternalMark.query.filter_by(
            student_id=student_id, subject_id=subject_id, exam_type=exam_type).first()
        student = User.query.get(student_id)
        if existing:
            existing.marks_obtained = marks
            existing.max_marks      = max_marks
            existing.uploaded_by    = session.get('user_id')
            existing.uploaded_at    = datetime.utcnow()
            message = f'Marks updated for {student.full_name}'
        else:
            mark = InternalMark(student_id=student_id, subject_id=subject_id,
                                exam_type=exam_type, marks_obtained=marks,
                                max_marks=max_marks, semester=student.semester,
                                uploaded_by=session.get('user_id'))
            db.session.add(mark)
            message = f'Marks saved for {student.full_name}'
        db.session.commit()
        return jsonify({'success': True, 'message': message, 'student_name': student.full_name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
```

- [ ] **Step 6: Commit**

```bash
git add controllers/teacher_controller.py
git commit -m "feat: scope all teacher routes to active classroom"
```

---

## Task 9: Create manage_classrooms.html template

**Files:**
- Create: `templates/admin/manage_classrooms.html`

- [ ] **Step 1: Create the file**

```html
{% extends "base.html" %}
{% block title %}Manage Classrooms - Admin{% endblock %}
{% block content %}
<div class="flex flex-col gap-6">
  <div class="flex justify-between items-center flex-wrap gap-4">
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
        <i data-lucide="school" class="h-8 w-8 text-primary"></i> Classrooms
      </h1>
      <p class="text-muted-foreground mt-1">Create and manage classrooms, assign students and teachers.</p>
    </div>
    <button onclick="document.getElementById('addClassroomModal').classList.remove('hidden')"
            class="shadcn-btn shadcn-btn-primary whitespace-nowrap">
      <i data-lucide="plus" class="mr-2 h-4 w-4"></i> Add Classroom
    </button>
  </div>

  <div class="shadcn-card overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-sm text-left align-middle">
        <thead class="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
          <tr>
            <th class="px-6 py-4 font-medium">Classroom</th>
            <th class="px-6 py-4 font-medium">Semester / Section</th>
            <th class="px-6 py-4 font-medium">Students</th>
            <th class="px-6 py-4 font-medium">Teachers</th>
            <th class="px-6 py-4 font-medium">Status</th>
            <th class="px-6 py-4 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          {% for item in classroom_data %}
          <tr class="hover:bg-muted/30 transition-colors">
            <td class="px-6 py-4 font-medium text-foreground">{{ item.classroom.name }}</td>
            <td class="px-6 py-4 text-muted-foreground">Sem {{ item.classroom.semester }} / {{ item.classroom.section }}</td>
            <td class="px-6 py-4">
              <span class="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                <i data-lucide="users" class="h-3 w-3"></i> {{ item.student_count }}
              </span>
            </td>
            <td class="px-6 py-4">
              <span class="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2 py-0.5 text-xs font-semibold text-purple-700">
                <i data-lucide="book-open" class="h-3 w-3"></i> {{ item.teacher_count }}
              </span>
            </td>
            <td class="px-6 py-4">
              {% if item.classroom.is_active %}
              <span class="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">Active</span>
              {% else %}
              <span class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-500">Inactive</span>
              {% endif %}
            </td>
            <td class="px-6 py-4 text-right">
              <a href="{{ url_for('admin.classroom_detail', cls_id=item.classroom.id) }}"
                 class="shadcn-btn shadcn-btn-outline text-xs py-1 px-3 mr-2">
                <i data-lucide="settings" class="h-3 w-3 mr-1"></i> Manage
              </a>
              <button onclick="deleteClassroom({{ item.classroom.id }}, '{{ item.classroom.name }}')"
                      class="shadcn-btn text-xs py-1 px-3 border border-destructive/40 text-destructive hover:bg-destructive/10">
                <i data-lucide="trash-2" class="h-3 w-3"></i>
              </button>
            </td>
          </tr>
          {% else %}
          <tr><td colspan="6" class="px-6 py-10 text-center text-muted-foreground">No classrooms yet. Click "Add Classroom" to create one.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- Add Classroom Modal -->
<div id="addClassroomModal" class="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
  <div class="bg-card rounded-2xl shadow-xl w-full max-w-md p-6 border border-border">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-xl font-bold text-foreground">Add Classroom</h2>
      <button onclick="document.getElementById('addClassroomModal').classList.add('hidden')" class="text-muted-foreground hover:text-foreground">
        <i data-lucide="x" class="h-5 w-5"></i>
      </button>
    </div>
    <form id="addClassroomForm" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Name *</label>
        <input name="name" type="text" placeholder="CSE 8th Sem A" required
               class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring">
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-foreground mb-1">Semester *</label>
          <input name="semester" type="number" min="1" max="10" placeholder="8" required
                 class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring">
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-1">Section *</label>
          <input name="section" type="text" maxlength="5" placeholder="A" required
                 class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring">
        </div>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Department *</label>
        <input name="department" type="text" placeholder="Computer Science" required
               class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring">
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Academic Year</label>
        <input name="academic_year" type="text" placeholder="2025-26"
               class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring">
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick="document.getElementById('addClassroomModal').classList.add('hidden')"
                class="shadcn-btn shadcn-btn-outline">Cancel</button>
        <button type="submit" class="shadcn-btn shadcn-btn-primary">Create Classroom</button>
      </div>
    </form>
  </div>
</div>

{% block extra_js %}
<script>
document.getElementById('addClassroomForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(this));
  const res  = await fetch('{{ url_for("admin.add_classroom") }}', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  });
  const json = await res.json();
  if (json.success) { location.reload(); }
  else { alert(json.message); }
});

async function deleteClassroom(id, name) {
  if (!confirm(`Deactivate classroom "${name}"?`)) return;
  const res  = await fetch(`/admin/classrooms/${id}/delete`, { method: 'POST' });
  const json = await res.json();
  if (json.success) { location.reload(); }
  else { alert(json.message); }
}
</script>
{% endblock %}
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/admin/manage_classrooms.html
git commit -m "feat: add manage_classrooms admin template"
```

---

## Task 10: Create classroom_detail.html template

**Files:**
- Create: `templates/admin/classroom_detail.html`

- [ ] **Step 1: Create the file**

```html
{% extends "base.html" %}
{% block title %}{{ cls.name }} - Admin{% endblock %}
{% block content %}
<div class="flex flex-col gap-6">
  <div class="flex items-center gap-4">
    <a href="{{ url_for('admin.manage_classrooms') }}" class="text-muted-foreground hover:text-foreground">
      <i data-lucide="arrow-left" class="h-5 w-5"></i>
    </a>
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
        <i data-lucide="school" class="h-8 w-8 text-primary"></i> {{ cls.name }}
      </h1>
      <p class="text-muted-foreground mt-1">Sem {{ cls.semester }} · Section {{ cls.section }} · {{ cls.department }}</p>
    </div>
  </div>

  <div class="grid gap-6 md:grid-cols-2">

    <!-- Students Panel -->
    <div class="shadcn-card flex flex-col">
      <div class="shadcn-card-header border-b border-border pb-4 flex items-center justify-between">
        <h3 class="shadcn-card-title flex items-center gap-2">
          <i data-lucide="users" class="h-5 w-5 text-primary"></i> Students ({{ students|length }})
        </h3>
        <button onclick="document.getElementById('addStudentModal').classList.remove('hidden')"
                class="shadcn-btn shadcn-btn-outline text-xs py-1 px-3">
          <i data-lucide="user-plus" class="h-3 w-3 mr-1"></i> Add
        </button>
      </div>
      <div class="flex flex-col divide-y divide-border max-h-96 overflow-y-auto">
        {% for s in students %}
        <div class="flex items-center justify-between px-4 py-3 hover:bg-muted/20">
          <div>
            <p class="text-sm font-medium text-foreground">{{ s.full_name }}</p>
            <p class="text-xs text-muted-foreground">{{ s.student_id }} · {{ s.email }}</p>
          </div>
          <button onclick="removeStudent({{ s.id }}, '{{ s.full_name }}')"
                  class="text-destructive hover:text-destructive/80 p-1">
            <i data-lucide="x" class="h-4 w-4"></i>
          </button>
        </div>
        {% else %}
        <div class="p-8 text-center text-muted-foreground text-sm">No students assigned yet.</div>
        {% endfor %}
      </div>
    </div>

    <!-- Teacher Assignments Panel -->
    <div class="shadcn-card flex flex-col">
      <div class="shadcn-card-header border-b border-border pb-4 flex items-center justify-between">
        <h3 class="shadcn-card-title flex items-center gap-2">
          <i data-lucide="book-open" class="h-5 w-5 text-primary"></i> Teacher Assignments ({{ assignments|length }})
        </h3>
        <button onclick="document.getElementById('addAssignmentModal').classList.remove('hidden')"
                class="shadcn-btn shadcn-btn-outline text-xs py-1 px-3">
          <i data-lucide="plus" class="h-3 w-3 mr-1"></i> Add
        </button>
      </div>
      <div class="flex flex-col divide-y divide-border max-h-96 overflow-y-auto">
        {% for a in assignments %}
        <div class="flex items-center justify-between px-4 py-3 hover:bg-muted/20">
          <div>
            <p class="text-sm font-medium text-foreground">{{ a.teacher.full_name }}</p>
            <p class="text-xs text-muted-foreground">{{ a.subject.code }} · {{ a.subject.name }}</p>
          </div>
          <button onclick="deleteAssignment({{ a.id }})"
                  class="text-destructive hover:text-destructive/80 p-1">
            <i data-lucide="trash-2" class="h-4 w-4"></i>
          </button>
        </div>
        {% else %}
        <div class="p-8 text-center text-muted-foreground text-sm">No assignments yet.</div>
        {% endfor %}
      </div>
    </div>
  </div>
</div>

<!-- Add Student Modal -->
<div id="addStudentModal" class="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
  <div class="bg-card rounded-2xl shadow-xl w-full max-w-md p-6 border border-border">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-bold">Add Student</h2>
      <button onclick="document.getElementById('addStudentModal').classList.add('hidden')">
        <i data-lucide="x" class="h-5 w-5 text-muted-foreground"></i>
      </button>
    </div>
    <select id="studentSelect" class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background mb-4">
      <option value="">-- Select unassigned student --</option>
      {% for s in unassigned %}
      <option value="{{ s.id }}">{{ s.full_name }} ({{ s.student_id }})</option>
      {% endfor %}
    </select>
    <div class="flex justify-end gap-3">
      <button onclick="document.getElementById('addStudentModal').classList.add('hidden')"
              class="shadcn-btn shadcn-btn-outline">Cancel</button>
      <button onclick="addStudent()" class="shadcn-btn shadcn-btn-primary">Add to Class</button>
    </div>
  </div>
</div>

<!-- Add Assignment Modal -->
<div id="addAssignmentModal" class="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
  <div class="bg-card rounded-2xl shadow-xl w-full max-w-md p-6 border border-border">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-bold">Add Assignment</h2>
      <button onclick="document.getElementById('addAssignmentModal').classList.add('hidden')">
        <i data-lucide="x" class="h-5 w-5 text-muted-foreground"></i>
      </button>
    </div>
    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium mb-1">Teacher</label>
        <select id="teacherSelect" class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background">
          <option value="">-- Select teacher --</option>
          {% for t in teachers %}
          <option value="{{ t.id }}">{{ t.full_name }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Subject</label>
        <select id="subjectSelect" class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background">
          <option value="">-- Select subject --</option>
          {% for s in subjects %}
          <option value="{{ s.id }}">{{ s.code }} - {{ s.name }}</option>
          {% endfor %}
        </select>
      </div>
    </div>
    <div class="flex justify-end gap-3 mt-4">
      <button onclick="document.getElementById('addAssignmentModal').classList.add('hidden')"
              class="shadcn-btn shadcn-btn-outline">Cancel</button>
      <button onclick="addAssignment()" class="shadcn-btn shadcn-btn-primary">Save Assignment</button>
    </div>
  </div>
</div>

{% block extra_js %}
<script>
const CLS_ID = {{ cls.id }};

async function addStudent() {
  const id = document.getElementById('studentSelect').value;
  if (!id) { alert('Select a student first'); return; }
  const res  = await fetch(`/admin/classrooms/${CLS_ID}/add-student`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ student_id: parseInt(id) })
  });
  const json = await res.json();
  if (json.success) { location.reload(); } else { alert(json.message); }
}

async function removeStudent(id, name) {
  if (!confirm(`Remove ${name} from this classroom?`)) return;
  const res  = await fetch(`/admin/classrooms/${CLS_ID}/remove-student`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ student_id: id })
  });
  const json = await res.json();
  if (json.success) { location.reload(); } else { alert(json.message); }
}

async function addAssignment() {
  const teacher_id = document.getElementById('teacherSelect').value;
  const subject_id = document.getElementById('subjectSelect').value;
  if (!teacher_id || !subject_id) { alert('Select both teacher and subject'); return; }
  const res  = await fetch(`/admin/classrooms/${CLS_ID}/add-assignment`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ teacher_id: parseInt(teacher_id), subject_id: parseInt(subject_id) })
  });
  const json = await res.json();
  if (json.success) { location.reload(); } else { alert(json.message); }
}

async function deleteAssignment(id) {
  if (!confirm('Remove this assignment?')) return;
  const res  = await fetch(`/admin/classrooms/assignments/${id}/delete`, { method: 'POST' });
  const json = await res.json();
  if (json.success) { location.reload(); } else { alert(json.message); }
}
</script>
{% endblock %}
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/admin/classroom_detail.html
git commit -m "feat: add classroom_detail admin template"
```

---

## Task 11: Update base.html — admin nav link + teacher classroom dropdown

**Files:**
- Modify: `templates/base.html`

- [ ] **Step 1: Add Classrooms link to admin sidebar (desktop)**

In the admin section of the desktop sidebar (around line 148, after the Users link), add:

```html
            <a href="{{ url_for('admin.manage_classrooms') }}"
                class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all {% if request.endpoint == 'admin.manage_classrooms' or request.endpoint == 'admin.classroom_detail' %}bg-secondary text-primary border-l-4 border-primary{% else %}text-muted-foreground hover:bg-secondary/50 hover:text-foreground{% endif %}">
                <i data-lucide="school" class="h-5 w-5"></i> Classrooms</a>
```

- [ ] **Step 2: Add teacher classroom dropdown at the top of the teacher sidebar section**

In the `{% elif session.role == 'TEACHER' %}` block (around line 115), insert this BEFORE the first `<a>` link:

```html
            {% if session.role == 'TEACHER' %}
            <!-- Classroom switcher for teachers -->
            <div class="mb-3 px-2">
              <p class="text-xs font-bold text-muted-foreground/60 uppercase tracking-wider mb-2 px-2">Active Class</p>
              <form action="{{ url_for('teacher.switch_classroom') }}" method="POST">
                <select name="classroom_id" onchange="this.form.submit()"
                        class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring font-semibold text-foreground">
                  {% for cls in teacher_classrooms %}
                  <option value="{{ cls.id }}" {% if cls.id == active_classroom_id %}selected{% endif %}>
                    {{ cls.name }}
                  </option>
                  {% endfor %}
                </select>
              </form>
            </div>
            <div class="border-t border-border/30 mb-2"></div>
            {% endif %}
```

- [ ] **Step 3: Mirror the Classrooms link in the mobile nav for admin**

In the mobile nav admin section (around line 236), add after the Users link:

```html
                <a href="{{ url_for('admin.manage_classrooms') }}" class="flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-bold {% if request.endpoint in ['admin.manage_classrooms', 'admin.classroom_detail'] %}bg-secondary text-primary{% else %}text-muted-foreground hover:bg-secondary/50 hover:text-foreground{% endif %}">
                    <i data-lucide="school" class="h-5 w-5"></i> Classrooms</a>
```

- [ ] **Step 4: Inject `teacher_classrooms` and `active_classroom_id` into the base template**

The dropdown needs these variables on every teacher page. Add a `context_processor` to `app.py` inside `create_app()`, after the blueprints are registered:

```python
    @app.context_processor
    def inject_teacher_context():
        from flask import session as flask_session
        if flask_session.get('role') == 'TEACHER':
            from models.teacher_assignment import TeacherAssignment
            from models.classroom import Classroom
            teacher_id = flask_session.get('user_id')
            classrooms = (db.session.query(Classroom)
                          .join(TeacherAssignment, TeacherAssignment.classroom_id == Classroom.id)
                          .filter(TeacherAssignment.teacher_id == teacher_id, Classroom.is_active == True)
                          .distinct().order_by(Classroom.name).all())
            active_id = flask_session.get('active_classroom_id')
            return {'teacher_classrooms': classrooms, 'active_classroom_id': active_id}
        return {'teacher_classrooms': [], 'active_classroom_id': None}
```

- [ ] **Step 5: Commit**

```bash
git add templates/base.html app.py
git commit -m "feat: add Classrooms nav link (admin) and classroom switcher dropdown (teacher)"
```

---

## Task 12: Update manage_users.html — classroom dropdown for student creation

**Files:**
- Modify: `templates/admin/manage_users.html`

- [ ] **Step 1: Pass classrooms to the manage_users route**

In `admin_controller.py`, update `manage_users()`:

```python
@admin_bp.route('/users')
@role_required('ADMIN')
def manage_users():
    from models.classroom import Classroom
    user = User.query.get(session.get('user_id'))
    role_filter = request.args.get('role', 'all')
    if role_filter == 'all':
        users = User.query.all()
    else:
        users = User.query.filter_by(role=role_filter.upper()).all()
    classrooms = Classroom.query.filter_by(is_active=True).order_by(Classroom.name).all()
    return render_template('admin/manage_users.html',
                           user=user, users=users,
                           role_filter=role_filter, classrooms=classrooms)
```

- [ ] **Step 2: Add classroom field to the Add User modal in the template**

In `templates/admin/manage_users.html`, find the student-specific fields section inside the Add User modal (where `semester` and `section` inputs are). Add after them:

```html
              <div id="classroomField" class="hidden">
                <label class="block text-sm font-medium text-foreground mb-1">Assign to Classroom</label>
                <select name="classroom_id"
                        class="w-full border border-input rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring">
                  <option value="">-- None (assign later) --</option>
                  {% for c in classrooms %}
                  <option value="{{ c.id }}">{{ c.name }}</option>
                  {% endfor %}
                </select>
              </div>
```

Also add JS to show/hide the field based on role selection (find the existing `roleSelect` change handler and add):

```javascript
  const classroomField = document.getElementById('classroomField');
  if (classroomField) {
    roleSelect.addEventListener('change', function() {
      classroomField.classList.toggle('hidden', this.value !== 'STUDENT');
    });
  }
```

- [ ] **Step 3: Add classroom column to the student rows in the users table**

In the table body for each user row, add in the student-specific section:

```html
{% if u.role == 'STUDENT' and u.classroom %}
<div class="text-[10px] text-primary mt-0.5 font-medium">{{ u.classroom.name }}</div>
{% elif u.role == 'STUDENT' %}
<div class="text-[10px] text-muted-foreground mt-0.5">No classroom</div>
{% endif %}
```

Place this inside the `<td>` that shows `u.full_name`, after the student_id line.

- [ ] **Step 4: Commit**

```bash
git add templates/admin/manage_users.html controllers/admin_controller.py
git commit -m "feat: add classroom dropdown to student creation form"
```

---

## Task 13: Update teacher templates

**Files:**
- Modify: `templates/teacher/dashboard.html`
- Modify: `templates/teacher/mark_attendance.html`
- Modify: `templates/teacher/view_students.html`
- Modify: `templates/teacher/class_attendance.html`
- Modify: `templates/teacher/enter_marks.html`

- [ ] **Step 1: Update `templates/teacher/dashboard.html`**

Replace the existing stats cards section and subjects list with classroom-aware versions. Replace the entire `{% block content %}` with:

```html
{% block content %}
<div class="flex flex-col gap-6">
  <div>
    <h1 class="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
      <i data-lucide="layout-dashboard" class="h-8 w-8 text-primary"></i> Teacher Dashboard
    </h1>
    {% if active_cls %}
    <p class="text-muted-foreground mt-1">
      Viewing: <span class="font-semibold text-foreground">{{ active_cls.name }}</span>
      · Sem {{ active_cls.semester }} · Section {{ active_cls.section }}
    </p>
    {% else %}
    <p class="text-muted-foreground mt-1">No classroom assigned. Contact admin.</p>
    {% endif %}
  </div>

  {% if not active_cls %}
  <div class="shadcn-card p-10 text-center text-muted-foreground">
    <i data-lucide="inbox" class="h-12 w-12 mx-auto mb-4 opacity-30"></i>
    <p class="text-lg font-medium">No classrooms assigned yet</p>
    <p class="text-sm mt-1">Ask an admin to assign you to a classroom.</p>
  </div>
  {% else %}

  <!-- Stats Cards -->
  <div class="grid gap-4 md:grid-cols-4">
    <div class="shadcn-card">
      <div class="shadcn-card-header flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 class="tracking-tight text-sm font-medium">Marked Today</h3>
        <i data-lucide="calendar-check" class="h-4 w-4 text-muted-foreground"></i>
      </div>
      <div class="shadcn-card-content">
        <div class="text-2xl font-bold text-primary">{{ marked_today }}</div>
        <p class="text-xs text-muted-foreground mt-1">Records added today</p>
      </div>
    </div>
    <div class="shadcn-card">
      <div class="shadcn-card-header flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 class="tracking-tight text-sm font-medium">Students</h3>
        <i data-lucide="users" class="h-4 w-4 text-muted-foreground"></i>
      </div>
      <div class="shadcn-card-content">
        <div class="text-2xl font-bold">{{ total_students }}</div>
        <p class="text-xs text-muted-foreground mt-1">In {{ active_cls.name }}</p>
      </div>
    </div>
    <div class="shadcn-card">
      <div class="shadcn-card-header flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 class="tracking-tight text-sm font-medium">Subjects Taught</h3>
        <i data-lucide="book-open" class="h-4 w-4 text-muted-foreground"></i>
      </div>
      <div class="shadcn-card-content">
        <div class="text-2xl font-bold">{{ subjects|length }}</div>
        <p class="text-xs text-muted-foreground mt-1">In this classroom</p>
      </div>
    </div>
    <div class="shadcn-card">
      <div class="shadcn-card-header flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 class="tracking-tight text-sm font-medium">At Risk</h3>
        <i data-lucide="alert-triangle" class="h-4 w-4 text-amber-500"></i>
      </div>
      <div class="shadcn-card-content">
        <div class="text-2xl font-bold {% if at_risk > 0 %}text-amber-500{% endif %}">{{ at_risk }}</div>
        <p class="text-xs text-muted-foreground mt-1">Below 75% attendance</p>
      </div>
    </div>
  </div>

  <!-- Main Grid -->
  <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
    <div class="flex flex-col gap-6 lg:col-span-4">
      <div class="shadcn-card">
        <div class="shadcn-card-header border-b border-border pb-4">
          <h3 class="shadcn-card-title flex items-center gap-2">
            <i data-lucide="zap" class="h-5 w-5 text-primary"></i> Quick Actions
          </h3>
        </div>
        <div class="shadcn-card-content pt-6">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <a href="{{ url_for('teacher.mark_attendance_page') }}"
               class="group rounded-xl border border-primary/20 bg-primary/5 p-6 hover:bg-primary/10 transition-colors flex flex-col items-center justify-center text-center gap-3">
              <div class="rounded-full bg-primary/20 p-3 text-primary group-hover:scale-110 transition-transform">
                <i data-lucide="camera" class="h-6 w-6"></i>
              </div>
              <div><h4 class="font-semibold text-foreground">Mark Attendance</h4>
              <p class="text-xs text-muted-foreground mt-1">For {{ active_cls.name }}</p></div>
            </a>
            <a href="{{ url_for('teacher.view_students') }}"
               class="group rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6 hover:bg-emerald-500/10 transition-colors flex flex-col items-center justify-center text-center gap-3">
              <div class="rounded-full bg-emerald-500/20 p-3 text-emerald-600 group-hover:scale-110 transition-transform">
                <i data-lucide="users-round" class="h-6 w-6"></i>
              </div>
              <div><h4 class="font-semibold text-foreground">View Students</h4>
              <p class="text-xs text-muted-foreground mt-1">{{ total_students }} students</p></div>
            </a>
            <a href="{{ url_for('teacher.class_attendance') }}"
               class="group rounded-xl border border-purple-500/20 bg-purple-500/5 p-6 hover:bg-purple-500/10 transition-colors flex flex-col items-center justify-center text-center gap-3">
              <div class="rounded-full bg-purple-500/20 p-3 text-purple-600 group-hover:scale-110 transition-transform">
                <i data-lucide="clipboard-list" class="h-6 w-6"></i>
              </div>
              <div><h4 class="font-semibold text-foreground">Class Attendance</h4>
              <p class="text-xs text-muted-foreground mt-1">View historical records</p></div>
            </a>
          </div>
        </div>
      </div>
    </div>
    <div class="flex flex-col gap-6 lg:col-span-3">
      <div class="shadcn-card">
        <div class="shadcn-card-header border-b border-border pb-4">
          <h3 class="shadcn-card-title flex items-center gap-2">
            <i data-lucide="book-open" class="h-5 w-5 text-primary"></i> Your Subjects in {{ active_cls.name }}
          </h3>
        </div>
        <div class="flex flex-col divide-y divide-border">
          {% for subject in subjects %}
          <div class="p-4 flex items-center gap-4 hover:bg-muted/20 transition-colors">
            <div class="h-10 w-10 shrink-0 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-xs uppercase">
              {{ subject.code[:2] }}
            </div>
            <div>
              <h6 class="font-semibold text-sm">{{ subject.code }}</h6>
              <span class="text-xs text-muted-foreground">{{ subject.name }}</span>
            </div>
          </div>
          {% else %}
          <div class="p-8 text-center text-muted-foreground text-sm">No subjects assigned in this classroom.</div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 2: Update `templates/teacher/mark_attendance.html` — replace student and subject dropdowns**

Find the lines in `mark_attendance.html` where `students` and `subjects` are iterated in the dropdowns. Replace the student `<select>` options with:

```html
{% for student in students %}
<option value="{{ student.id }}">{{ student.full_name }} ({{ student.student_id }})</option>
{% else %}
<option disabled>No students in active classroom</option>
{% endfor %}
```

And the subject `<select>` options with:

```html
{% for subject in subjects %}
<option value="{{ subject.id }}">{{ subject.code }} - {{ subject.name }}</option>
{% else %}
<option disabled>No subjects assigned</option>
{% endfor %}
```

Add a classroom banner at the top of the `{% block content %}` (before the existing `<div class="flex flex-col gap-6">`):

```html
{% if active_cls %}
<div class="mb-4 px-4 py-2 rounded-lg bg-primary/5 border border-primary/20 text-sm text-foreground font-medium flex items-center gap-2">
  <i data-lucide="school" class="h-4 w-4 text-primary"></i>
  Marking attendance for: <span class="text-primary font-bold">{{ active_cls.name }}</span>
</div>
{% endif %}
```

- [ ] **Step 3: Update `templates/teacher/view_students.html` — remove old filter controls, show classroom context**

Add at the top of `{% block content %}`:

```html
{% if active_cls %}
<div class="mb-4 px-4 py-2 rounded-lg bg-primary/5 border border-primary/20 text-sm font-medium flex items-center gap-2">
  <i data-lucide="school" class="h-4 w-4 text-primary"></i>
  Showing students in: <span class="text-primary font-bold">{{ active_cls.name }}</span>
  <span class="ml-auto text-muted-foreground">{{ total_students }} student(s)</span>
</div>
{% endif %}
```

Remove the old department/semester/section filter `<form>` block (the `<div class="flex gap-4...">` filter area) since filtering is now by classroom. Keep the table body untouched.

- [ ] **Step 4: Update `templates/teacher/class_attendance.html` — scope subject dropdown**

In the subject dropdown in the filter form, replace the options with:

```html
{% for subject in subjects %}
<option value="{{ subject.id }}" {% if selected_subject and selected_subject.id == subject.id %}selected{% endif %}>
  {{ subject.code }} - {{ subject.name }}
</option>
{% else %}
<option disabled>No subjects assigned to this classroom</option>
{% endfor %}
```

- [ ] **Step 5: Update `templates/teacher/enter_marks.html` — scope subject and student dropdowns**

Replace student options:

```html
{% for student in students %}
<option value="{{ student.id }}">{{ student.full_name }} ({{ student.student_id }})</option>
{% else %}
<option disabled>No students in active classroom</option>
{% endfor %}
```

Replace subject options:

```html
{% for subject in subjects %}
<option value="{{ subject.id }}">{{ subject.code }} - {{ subject.name }}</option>
{% else %}
<option disabled>No subjects assigned</option>
{% endfor %}
```

- [ ] **Step 6: Commit**

```bash
git add templates/teacher/
git commit -m "feat: update teacher templates to show classroom-scoped data"
```

---

## Task 14: Smoke test and final reset

- [ ] **Step 1: Reset DB and start app**

```bash
rm -f database/attendance.db
python app.py
```

Expected startup output includes:
```
Seeded 60 students, XXXX attendance records.
Face Recognition Attendance System Started!
```

- [ ] **Step 2: Verify admin flows**

- Login as `admin` / `admin123`
- Navigate to Classrooms in sidebar → should see "CSE 8th Sem A" and "CSE 8th Sem B"
- Click "Manage" on Sem A → should see 30 students and 3 teacher assignments
- Click "Add Classroom" → create a test classroom → verify it appears in the list
- Delete the test classroom → verify it is marked inactive

- [ ] **Step 3: Verify teacher flows**

- Logout, login as `teacher1` / `teacher123`
- Sidebar shows a classroom dropdown — "CSE 8th Sem A" should be selected
- Dashboard stats cards show Sem A students (30) and subjects (CS501, CS502)
- Switch to "CSE 8th Sem B" via the dropdown → stats update to show CS503 subject
- Navigate to Mark Attendance → student list shows only Sem B students; subject dropdown shows CS503
- Navigate to View Students → only Sem B students shown
- Navigate to Enter Marks → subjects limited to CS503

- [ ] **Step 4: Verify student attendance data**

```bash
python - <<'EOF'
from app import create_app
app = create_app()
with app.app_context():
    from models.attendance import Attendance
    total = Attendance.query.count()
    print(f"Total attendance records: {total}")
    assert total > 1000, f"Expected >1000 records, got {total}"
    print("OK")
EOF
```

Expected: prints total > 1000 and "OK".

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete classroom & teacher management with seeded attendance data"
```
