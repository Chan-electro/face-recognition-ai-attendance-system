import random
from datetime import datetime, date, timedelta, time as dtime


def init_database(app):
    """Initialize database and create tables"""
    from models import db
    with app.app_context():
        db.create_all()
        print("Database tables created")


def seed_database(app):
    """Seed database with initial data including classrooms and attendance history."""
    with app.app_context():
        from models.user import User
        if User.query.first():
            print("Database already contains data. Skipping seed.")
            return

        print("Seeding database...")
        from models import db
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
        timetable_data = [
            (0, 'MONDAY',    dtime(9, 0),  dtime(10, 0), 'Room 101'),
            (1, 'MONDAY',    dtime(10, 0), dtime(11, 0), 'Room 102'),
            (2, 'MONDAY',    dtime(11, 30), dtime(12, 30), 'Room 103'),
            (3, 'TUESDAY',   dtime(9, 0),  dtime(10, 0), 'Room 101'),
            (4, 'TUESDAY',   dtime(10, 0), dtime(11, 0), 'Room 102'),
            (0, 'WEDNESDAY', dtime(9, 0),  dtime(10, 0), 'Room 101'),
            (2, 'WEDNESDAY', dtime(10, 0), dtime(11, 0), 'Room 103'),
            (1, 'THURSDAY',  dtime(9, 0),  dtime(10, 0), 'Room 102'),
            (4, 'FRIDAY',    dtime(9, 0),  dtime(10, 0), 'Room 102'),
        ]
        for subj_idx, day, start, end, room in timetable_data:
            entry = Timetable(subject_id=subject_objects[subj_idx].id,
                              day_of_week=day, start_time=start, end_time=end,
                              room=room, semester=5, department='Computer Science')
            db.session.add(entry)
        db.session.commit()

        # ── Students (60 total, 30 per classroom) ────────────
        random.seed(42)

        def presence_rate(idx):
            if idx < 36:
                return random.uniform(0.75, 0.92)
            elif idx < 51:
                return random.uniform(0.55, 0.74)
            else:
                return random.uniform(0.93, 1.00)

        all_students = []
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
        cls_a_subjects = [s501, s502, s503]
        cls_b_subjects = [s503, s504, s505]

        attendance_records = []
        for student, rate in all_students:
            subjects = cls_a_subjects if student.section == 'A' else cls_b_subjects
            for subject in subjects:
                for day_offset in range(30):
                    att_date = today - timedelta(days=day_offset + 1)
                    if att_date.weekday() >= 5:  # skip weekends
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

        chunk = 500
        for start in range(0, len(attendance_records), chunk):
            db.session.add_all(attendance_records[start:start + chunk])
            db.session.commit()

        print(f"Seeded {len(all_students)} students, {len(attendance_records)} attendance records.")
        print("\nDefault credentials:")
        print("  Admin:   admin / admin123")
        print("  Teacher: teacher1 / teacher123")
        print("  Student: student1 / student123\n")


def _student_name(idx):
    """Return a plausible Indian name for the given zero-based index."""
    first = [
        'Rahul', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Ananya', 'Rohan', 'Kavita', 'Arjun', 'Megha',
        'Karan', 'Divya', 'Siddharth', 'Pooja', 'Aditya', 'Riya', 'Nikhil', 'Shruti', 'Varun', 'Neha',
        'Deepak', 'Ankita', 'Rajat', 'Swati', 'Harsh', 'Preeti', 'Mohit', 'Kajal', 'Sachin', 'Shweta',
        'Aman', 'Simran', 'Gaurav', 'Nisha', 'Vivek', 'Tanvi', 'Aakash', 'Pallavi', 'Pranav', 'Juhi',
        'Suresh', 'Meena', 'Vishal', 'Sonal', 'Tarun', 'Bhavna', 'Manish', 'Rekha', 'Hemant', 'Usha',
        'Lalit', 'Geeta', 'Naveen', 'Sunita', 'Rohit', 'Madhu', 'Ajay', 'Sita', 'Ankit', 'Gita',
    ]
    last = [
        'Verma', 'Singh', 'Patel', 'Reddy', 'Sharma', 'Gupta', 'Das', 'Iyer', 'Nair', 'Kapoor',
        'Kumar', 'Mishra', 'Joshi', 'Shah', 'Yadav', 'Tiwari', 'Rao', 'Pillai', 'Menon', 'Chauhan',
        'Bose', 'Ghosh', 'Chatterjee', 'Mukherjee', 'Sen', 'Roy', 'Dey', 'Saha', 'Paul', 'Biswas',
        'Desai', 'Mehta', 'Gandhi', 'Modi', 'Trivedi', 'Pandya', 'Bhatt', 'Jain', 'Agarwal', 'Bansal',
        'Malhotra', 'Khanna', 'Bhatia', 'Arora', 'Sethi', 'Luthra', 'Chopra', 'Tandon', 'Grover', 'Anand',
        'Saxena', 'Srivastava', 'Dubey', 'Awasthi', 'Tripathi', 'Shukla', 'Pandey', 'Upadhyay', 'Bajpai', 'Misra',
    ]
    return f"{first[idx % len(first)]} {last[idx % len(last)]}"


def reset_database(app):
    """Reset database (drop all tables and recreate)"""
    from models import db
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset complete")
