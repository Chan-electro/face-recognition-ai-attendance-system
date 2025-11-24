from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models for easy access
from models.user import User
from models.attendance import Attendance
from models.face_encoding import FaceEncoding
from models.subject import Subject
from models.faculty import Faculty
from models.timetable import Timetable
