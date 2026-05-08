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
    """View student list with filters"""
    user = User.query.get(session.get('user_id'))

    # Filter params
    dept_filter = request.args.get('department', '').strip()
    sem_filter = request.args.get('semester', type=int)
    sec_filter = request.args.get('section', '').strip()

    # Build query
    query = User.query.filter_by(role='STUDENT', is_active=True)
    if dept_filter:
        query = query.filter_by(department=dept_filter)
    if sem_filter:
        query = query.filter_by(semester=sem_filter)
    if sec_filter:
        query = query.filter_by(section=sec_filter)

    students = query.order_by(User.full_name).all()

    # Get attendance stats for each student
    student_data = []
    for student in students:
        stats = AttendanceService.get_attendance_stats(student.id)
        student_data.append({
            'student': student,
            'stats': stats
        })

    # Distinct values for filter dropdowns
    all_students = User.query.filter_by(role='STUDENT', is_active=True).all()
    departments = sorted(set(s.department for s in all_students if s.department))
    semesters = sorted(set(s.semester for s in all_students if s.semester))
    sections = sorted(set(s.section for s in all_students if s.section))

    context = {
        'user': user,
        'student_data': student_data,
        'departments': departments,
        'semesters': semesters,
        'sections': sections,
        'dept_filter': dept_filter,
        'sem_filter': sem_filter,
        'sec_filter': sec_filter,
        'total_students': len(student_data)
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


@teacher_bp.route('/upload-attendance')
@role_required('TEACHER')
def upload_attendance_page():
    """Attendance upload page for teachers"""
    user = User.query.get(session.get('user_id'))
    return render_template('teacher/upload_attendance.html', user=user)


@teacher_bp.route('/upload-attendance', methods=['POST'])
@role_required('TEACHER')
def upload_attendance():
    """Handle attendance Excel/CSV upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        from utils.file_utils import save_uploaded_file
        filepath = save_uploaded_file(file, 'exports')
        if not filepath:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400

        from services.excel_service import ExcelService
        result = ExcelService.import_attendance(filepath, uploaded_by=session.get('user_id'))

        import os
        try:
            os.remove(filepath)
        except OSError:
            pass

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@teacher_bp.route('/notes')
@role_required('TEACHER')
def notes_page():
    """Teacher notes management"""
    user = User.query.get(session.get('user_id'))
    subjects = Subject.query.filter_by(is_active=True).all()

    from models.note import Note
    notes = Note.query.filter_by(uploaded_by=user.id, is_active=True).order_by(Note.uploaded_at.desc()).all()

    context = {
        'user': user,
        'subjects': subjects,
        'notes': notes
    }
    return render_template('teacher/notes.html', **context)


@teacher_bp.route('/notes/upload', methods=['POST'])
@role_required('TEACHER')
def upload_note():
    """Upload a new note/study material"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400

        file = request.files['file']
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        subject_id = request.form.get('subject_id')

        if not title or not subject_id:
            return jsonify({'success': False, 'message': 'Title and Subject are required'}), 400

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        from flask import current_app
        from utils.file_utils import save_uploaded_file
        filepath = save_uploaded_file(file, 'notes')

        if not filepath:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400

        import os
        file_size = os.path.getsize(filepath)
        user = User.query.get(session.get('user_id'))

        from models.note import Note
        note = Note(
            title=title,
            description=description,
            filename=os.path.basename(filepath),
            filepath=filepath,
            file_size=file_size,
            subject_id=int(subject_id),
            uploaded_by=user.id,
            semester=user.semester,
            department=user.department
        )
        db.session.add(note)
        db.session.commit()

        return jsonify({'success': True, 'message': f'Note "{title}" uploaded successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@teacher_bp.route('/notes/<int:note_id>/delete', methods=['POST'])
@role_required('TEACHER')
def delete_note(note_id):
    """Delete a note"""
    try:
        from models.note import Note
        note = Note.query.get(note_id)
        if not note:
            return jsonify({'success': False, 'message': 'Note not found'}), 404

        note.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Note deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
