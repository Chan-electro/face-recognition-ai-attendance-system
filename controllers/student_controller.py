from flask import Blueprint, render_template, session, jsonify, request
from utils.auth_utils import login_required, role_required
from models.user import User
from models.subject import Subject
from models.timetable import Timetable
from models.faculty import Faculty
from services.attendance_service import AttendanceService
from datetime import datetime, timedelta

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@role_required('STUDENT')
def dashboard():
    """Student dashboard"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Get overall attendance stats
    overall_stats = AttendanceService.get_attendance_stats(user_id)
    
    # Get subject-wise attendance
    subject_attendance = AttendanceService.get_subject_wise_attendance(user_id)
    
    # Get recent attendance
    recent_attendance = AttendanceService.get_recent_attendance(user_id, limit=5)
    
    # Check if below minimum attendance
    min_attendance = 75
    is_below_minimum = overall_stats['percentage'] < min_attendance
    
    context = {
        'user': user,
        'overall_stats': overall_stats,
        'subject_attendance': subject_attendance,
        'recent_attendance': recent_attendance,
        'is_below_minimum': is_below_minimum,
        'min_attendance': min_attendance
    }
    
    return render_template('student/dashboard.html', **context)


@student_bp.route('/attendance')
@role_required('STUDENT')
def attendance():
    """Detailed attendance view"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Get subject filter from query params
    subject_id = request.args.get('subject_id', type=int)
    
    # Get subject-wise attendance
    subject_attendance = AttendanceService.get_subject_wise_attendance(user_id)
    
    # Get all subjects for filter dropdown
    subjects = Subject.query.filter_by(is_active=True).all()
    
    # Get attendance records
    if subject_id:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)  # Last 3 months
        records = AttendanceService.get_attendance_by_date_range(
            user_id, start_date, end_date, subject_id
        )
        selected_subject = Subject.query.get(subject_id)
    else:
        records = AttendanceService.get_recent_attendance(user_id, limit=50)
        selected_subject = None
    
    context = {
        'user': user,
        'subject_attendance': subject_attendance,
        'subjects': subjects,
        'selected_subject': selected_subject,
        'records': records
    }
    
    return render_template('student/attendance.html', **context)


@student_bp.route('/ai-assistant')
@role_required('STUDENT')
def ai_assistant():
    """AI assistant chatbot page"""
    user = User.query.get(session.get('user_id'))
    return render_template('student/ai_assistant.html', user=user)


@student_bp.route('/subjects')
@role_required('STUDENT')
def subjects():
    """View subjects and faculty"""
    user = User.query.get(session.get('user_id'))
    
    # Get all active subjects
    all_subjects = Subject.query.filter_by(is_active=True).all()
    
    # Get subject-wise attendance for this student
    subject_attendance = AttendanceService.get_subject_wise_attendance(user.id)
    
    # Create a mapping of subject_id to attendance stats
    attendance_map = {sa['subject_id']: sa for sa in subject_attendance}
    
    context = {
        'user': user,
        'subjects': all_subjects,
        'attendance_map': attendance_map
    }
    
    return render_template('student/subjects.html', **context)


@student_bp.route('/timetable')
@role_required('STUDENT')
def timetable():
    """View class timetable"""
    user = User.query.get(session.get('user_id'))
    
    # Get timetable for student's semester and department
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']
    schedule = {}
    
    for day in days:
        entries = Timetable.get_schedule_for_day(
            day,
            semester=user.semester,
            department=user.department
        )
        schedule[day] = [entry.to_dict() for entry in entries]
    
    context = {
        'user': user,
        'schedule': schedule,
        'days': days
    }
    
    return render_template('student/timetable.html', **context)


@student_bp.route('/improvement-suggestions')
@role_required('STUDENT')
def improvement_suggestions():
    """Get attendance improvement suggestions"""
    user_id = session.get('user_id')
    subject_id = request.args.get('subject_id', type=int)
    
    if subject_id:
        # Get required classes for specific subject
        result = AttendanceService.calculate_required_classes(user_id, subject_id)
        subject = Subject.query.get(subject_id)
        result['subject_name'] = subject.name if subject else 'Unknown'
    else:
        # Get overall suggestion
        overall_stats = AttendanceService.get_attendance_stats(user_id)
        result = {
            'current_percentage': overall_stats['percentage'],
            'message': 'Check individual subjects for specific improvement suggestions'
        }
    
    return jsonify(result)


@student_bp.route('/profile')
@role_required('STUDENT')
def profile():
    """Student profile page"""
    user = User.query.get(session.get('user_id'))
    
    # Get overall stats
    overall_stats = AttendanceService.get_attendance_stats(user.id)
    
    context = {
        'user': user,
        'overall_stats': overall_stats
    }
    
    return render_template('student/profile.html', **context)


