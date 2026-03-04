from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from utils.auth_utils import role_required
from models import db
from models.user import User
from models.subject import Subject
from models.attendance import Attendance
from services.face_recognition_service import get_face_service
from services.attendance_service import AttendanceService
from services.report_service import ReportService
from datetime import datetime, date
import base64

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')


@teacher_bp.route('/dashboard')
@role_required('TEACHER')
def dashboard():
    """Teacher dashboard"""
    user = User.query.get(session.get('user_id'))
    
    # Get subjects taught by this teacher (simplified - assumes faculty table links)
    subjects = Subject.query.filter_by(is_active=True).all()
    
    # Get today's classes marked
    today = date.today()
    marked_today = Attendance.query.filter_by(
        marked_by=user.id,
        date=today
    ).count()
    
    # Get total students
    total_students = User.query.filter_by(role='STUDENT', is_active=True).count()
    
    context = {
        'user': user,
        'subjects': subjects,
        'marked_today': marked_today,
        'total_students': total_students
    }
    
    return render_template('teacher/dashboard.html', **context)


@teacher_bp.route('/mark-attendance', methods=['GET'])
@role_required('TEACHER')
def mark_attendance_page():
    """Attendance marking page"""
    user = User.query.get(session.get('user_id'))
    subjects = Subject.query.filter_by(is_active=True).all()
    students = User.query.filter_by(role='STUDENT', is_active=True).all()
    
    context = {
        'user': user,
        'subjects': subjects,
        'students': students
    }
    
    return render_template('teacher/mark_attendance.html', **context)


@teacher_bp.route('/mark-attendance', methods=['POST'])
@role_required('TEACHER')
def mark_attendance():
    """Manually mark attendance for a student"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        student_id = data.get('student_id')
        subject_id = data.get('subject_id')
        status = data.get('status', 'PRESENT')
        
        if not student_id or not subject_id:
            return jsonify({'success': False, 'message': 'Missing student or subject'}), 400
        
        # Mark attendance
        attendance = AttendanceService.mark_attendance(
            student_id=student_id,
            subject_id=subject_id,
            status=status,
            marked_by=session.get('user_id'),
            confidence_score=1.0, # Manual attendance
            is_manual=True
        )
        
        if attendance:
            student = User.query.get(student_id)
            return jsonify({
                'success': True,
                'message': f"Attendance marked {status} for {student.full_name}",
                'student_name': student.full_name
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to mark attendance'}), 500
            
    except Exception as e:
        print(f"Error in mark_attendance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500



@teacher_bp.route('/students')
@role_required('TEACHER')
def view_students():
    """View student list"""
    user = User.query.get(session.get('user_id'))
    
    # Get all active students
    students = User.query.filter_by(role='STUDENT', is_active=True).all()
    
    # Get attendance stats for each student
    student_data = []
    for student in students:
        stats = AttendanceService.get_attendance_stats(student.id)
        student_data.append({
            'student': student,
            'stats': stats
        })
    
    context = {
        'user': user,
        'student_data': student_data
    }
    
    return render_template('teacher/view_students.html', **context)


@teacher_bp.route('/class-attendance')
@role_required('TEACHER')
def class_attendance():
    """View attendance for a specific class"""
    user = User.query.get(session.get('user_id'))
    
    subject_id = request.args.get('subject_id', type=int)
    date_str = request.args.get('date')
    
    if date_str:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        attendance_date = date.today()
    
    subjects = Subject.query.filter_by(is_active=True).all()
    
    if subject_id:
        records = AttendanceService.get_class_attendance(subject_id, attendance_date)
        selected_subject = Subject.query.get(subject_id)
    else:
        records = []
        selected_subject = None
    
    context = {
        'user': user,
        'subjects': subjects,
        'selected_subject': selected_subject,
        'attendance_date': attendance_date,
        'records': records
    }
    
    return render_template('teacher/class_attendance.html', **context)


@teacher_bp.route('/download-report')
@role_required('TEACHER')
def download_report():
    """Download class attendance report"""
    from flask import make_response
    
    subject_id = request.args.get('subject_id', type=int)
    date_str = request.args.get('date')
    
    if not subject_id:
        flash('Please select a subject', 'warning')
        return redirect(url_for('teacher.class_attendance'))
    
    if date_str:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        attendance_date = date.today()
    
    # Generate CSV report
    csv_data = ReportService.generate_class_report_csv(subject_id, attendance_date)
    
    if csv_data:
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = f'attachment; filename=attendance_{subject_id}_{attendance_date}.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    else:
        flash('Failed to generate report', 'danger')
        return redirect(url_for('teacher.class_attendance'))
