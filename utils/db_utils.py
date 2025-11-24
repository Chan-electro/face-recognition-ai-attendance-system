from datetime import datetime, date
from models import db
from models.user import User
from models.faculty import Faculty
from models.subject import Subject
from models.timetable import Timetable


def init_database(app):
    """Initialize database and create tables"""
    with app.app_context():
        db.create_all()
        print("✓ Database tables created")


def seed_database(app):
    """Seed database with initial data"""
    with app.app_context():
        # Check if data already exists
        if User.query.first():
            print("Database already contains data. Skipping seed.")
            return
        
        print("Seeding database...")
        
        # Create Admin
        admin = User(
            username='admin',
            email='admin@college.edu',
            full_name='System Administrator',
            role='ADMIN',
            department='Administration'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create Teachers
        teacher1 = User(
            username='teacher1',
            email='rajesh.kumar@college.edu',
            full_name='Dr. Rajesh Kumar',
            role='TEACHER',
            department='Computer Science'
        )
        teacher1.set_password('teacher123')
        db.session.add(teacher1)
        
        teacher2 = User(
            username='teacher2',
            email='anjali.sharma@college.edu',
            full_name='Prof. Anjali Sharma',
            role='TEACHER',
            department='Computer Science'
        )
        teacher2.set_password('teacher123')
        db.session.add(teacher2)
        
        # Create Students (10 students)
        students_data = [
            ('student1', 'CS001', 'Rahul Verma', 'rahul.verma@student.college.edu', 5),
            ('student2', 'CS002', 'Priya Singh', 'priya.singh@student.college.edu', 5),
            ('student3', 'CS003', 'Amit Patel', 'amit.patel@student.college.edu', 5),
            ('student4', 'CS004', 'Sneha Reddy', 'sneha.reddy@student.college.edu', 5),
            ('student5', 'CS005', 'Vikram Sharma', 'vikram.sharma@student.college.edu', 5),
            ('student6', 'CS006', 'Ananya Gupta', 'ananya.gupta@student.college.edu', 5),
            ('student7', 'CS007', 'Rohan Das', 'rohan.das@student.college.edu', 5),
            ('student8', 'CS008', 'Kavita Iyer', 'kavita.iyer@student.college.edu', 5),
            ('student9', 'CS009', 'Arjun Nair', 'arjun.nair@student.college.edu', 5),
            ('student10', 'CS010', 'Megha Kapoor', 'megha.kapoor@student.college.edu', 5),
        ]
        
        for username, student_id, full_name, email, semester in students_data:
            student = User(
                username=username,
                email=email,
                full_name=full_name,
                role='STUDENT',
                student_id=student_id,
                department='Computer Science',
                semester=semester
            )
            student.set_password('student123')
            db.session.add(student)
        
        db.session.commit()
        print("✓ Users created")
        
        # Create Faculty
        faculty_data = [
            ('Dr. Rajesh Kumar', 'Professor', 'Computer Science', 'rajesh.kumar@college.edu', 
             '9876543210', 'CS-301', 'Data Structures, Algorithms'),
            ('Prof. Anjali Sharma', 'Assistant Professor', 'Computer Science', 'anjali.sharma@college.edu',
             '9876543211', 'CS-302', 'Operating Systems, Computer Networks'),
            ('Dr. Vikram Singh', 'Associate Professor', 'Computer Science', 'vikram.singh@college.edu',
             '9876543212', 'CS-303', 'Database Management, Software Engineering'),
            ('Prof. Meera Nair', 'Assistant Professor', 'Computer Science', 'meera.nair@college.edu',
             '9876543213', 'CS-304', 'Web Technologies, Mobile Computing'),
            ('Dr. Sanjay Gupta', 'Professor', 'Computer Science', 'sanjay.gupta@college.edu',
             '9876543214', 'CS-305', 'Artificial Intelligence, Machine Learning'),
        ]
        
        faculty_objects = []
        for name, designation, dept, email, phone, office, spec in faculty_data:
            faculty = Faculty(
                name=name,
                designation=designation,
                department=dept,
                email=email,
                phone=phone,
                office=office,
                specialization=spec
            )
            db.session.add(faculty)
            faculty_objects.append(faculty)
        
        db.session.commit()
        print("✓ Faculty created")
        
        # Create Subjects
        subjects_data = [
            ('CS501', 'Data Structures and Algorithms', 'Advanced data structures and algorithm design', 4, 5, 0),
            ('CS502', 'Operating Systems', 'Process management, memory management, file systems', 4, 5, 1),
            ('CS503', 'Database Management Systems', 'Relational databases, SQL, normalization', 4, 5, 2),
            ('CS504', 'Web Technologies', 'HTML, CSS, JavaScript, Flask, React', 3, 5, 3),
            ('CS505', 'Computer Networks', 'Network protocols, TCP/IP, network security', 4, 5, 1),
            ('CS506', 'Artificial Intelligence', 'Search algorithms, logic, machine learning basics', 3, 5, 4),
            ('CS507', 'Software Engineering', 'SDLC, agile methodologies, testing', 3, 5, 2),
        ]
        
        subject_objects = []
        for code, name, desc, credits, sem, fac_idx in subjects_data:
            subject = Subject(
                code=code,
                name=name,
                description=desc,
                credits=credits,
                semester=sem,
                department='Computer Science',
                faculty_id=faculty_objects[fac_idx].id
            )
            db.session.add(subject)
            subject_objects.append(subject)
        
        db.session.commit()
        print("✓ Subjects created")
        
        # Create Timetable
        from datetime import time
        
        timetable_data = [
            # Monday
            (0, 'MONDAY', time(9, 0), time(10, 0), 'Room 101'),
            (1, 'MONDAY', time(10, 0), time(11, 0), 'Room 102'),
            (2, 'MONDAY', time(11, 30), time(12, 30), 'Room 103'),
            (5, 'MONDAY', time(14, 0), time(15, 0), 'Lab 1'),
            # Tuesday
            (3, 'TUESDAY', time(9, 0), time(10, 0), 'Room 101'),
            (4, 'TUESDAY', time(10, 0), time(11, 0), 'Room 102'),
            (6, 'TUESDAY', time(11, 30), time(12, 30), 'Room 103'),
            (0, 'TUESDAY', time(14, 0), time(16, 0), 'Lab 2'),
            # Wednesday
            (0, 'WEDNESDAY', time(9, 0), time(10, 0), 'Room 101'),
            (2, 'WEDNESDAY', time(10, 0), time(11, 0), 'Room 103'),
            (1, 'WEDNESDAY', time(11, 30), time(12, 30), 'Room 102'),
            (3, 'WEDNESDAY', time(14, 0), time(15, 0), 'Lab 1'),
            # Thursday
            (1, 'THURSDAY', time(9, 0), time(10, 0), 'Room 102'),
            (3, 'THURSDAY', time(11, 30), time(12, 30), 'Room 101'),
            (5, 'THURSDAY', time(14, 0), time(15, 0), 'Room 103'),
            (6, 'THURSDAY', time(15, 0), time(16, 0), 'Room 103'),
            # Friday
            (4, 'FRIDAY', time(9, 0), time(10, 0), 'Room 102'),
            (0, 'FRIDAY', time(10, 0), time(11, 0), 'Room 101'),
            (2, 'FRIDAY', time(11, 30), time(12, 30), 'Room 103'),
            (5, 'FRIDAY', time(14, 0), time(16, 0), 'Lab 3'),
        ]
        
        for subj_idx, day, start, end, room in timetable_data:
            entry = Timetable(
                subject_id=subject_objects[subj_idx].id,
                day_of_week=day,
                start_time=start,
                end_time=end,
                room=room,
                semester=5,
                department='Computer Science'
            )
            db.session.add(entry)
        
        db.session.commit()
        print("✓ Timetable created")
        
        print("\n" + "="*50)
        print("Database seeded successfully!")
        print("="*50)
        print("\nDefault Login Credentials:")
        print("-" * 50)
        print("Admin:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nTeacher:")
        print("  Username: teacher1 or teacher2")
        print("  Password: teacher123")
        print("\nStudent:")
        print("  Username: student1, student2, student3, student4, student5")
        print("  Password: student123")
        print("="*50 + "\n")


def reset_database(app):
    """Reset database (drop all tables and recreate)"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset complete")
