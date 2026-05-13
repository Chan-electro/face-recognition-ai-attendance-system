from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from utils.auth_utils import role_required
from models import db
from models.user import User
from models.subject import Subject
from models.attendance import Attendance
from services.face_recognition_service import get_face_service
from services.attendance_service import AttendanceService
from services.report_service import ReportService
from services.excel_service import ExcelService
from models.internal_mark import InternalMark
from datetime import datetime, date
import base64

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')


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
    session['active_classroom_id'] = classrooms[0].id
    return classrooms[0]


def _get_classroom_subjects(teacher_id, classroom_id):
    """Return Subject objects this teacher teaches in the given classroom."""
    from models.teacher_assignment import TeacherAssignment
    rows = (TeacherAssignment.query
            .filter_by(teacher_id=teacher_id, classroom_id=classroom_id)
            .all())
    return [r.subject for r in rows]


@teacher_bp.route('/switch-classroom', methods=['POST'])
@role_required('TEACHER')
def switch_classroom():
    teacher_id = session.get('user_id')
    cls_id = request.form.get('classroom_id', type=int)
    classrooms = _get_teacher_classrooms(teacher_id)
    if cls_id and any(c.id == cls_id for c in classrooms):
        session['active_classroom_id'] = cls_id
    return redirect(request.referrer or url_for('teacher.dashboard'))


@teacher_bp.route('/dashboard')
@role_required('TEACHER')
def dashboard():
    teacher_id = session.get('user_id')
    user       = User.query.get(teacher_id)
    classrooms = _get_teacher_classrooms(teacher_id)
    active_cls = _get_active_classroom(teacher_id)

    if not active_cls:
        return render_template('teacher/dashboard.html',
                               user=user, classrooms=classrooms, active_cls=None,
                               subjects=[], marked_today=0, total_students=0, at_risk=0)

    subjects = _get_classroom_subjects(teacher_id, active_cls.id)
    today    = date.today()

    marked_today   = Attendance.query.filter_by(marked_by=teacher_id, date=today).count()
    total_students = active_cls.students.filter_by(is_active=True).count()

    at_risk = 0
    for student in active_cls.students.filter_by(is_active=True).all():
        stats = AttendanceService.get_attendance_stats(student.id)
        if stats['total'] > 0 and stats['percentage'] < 75:
            at_risk += 1

    return render_template('teacher/dashboard.html',
                           user=user, classrooms=classrooms, active_cls=active_cls,
                           subjects=subjects, marked_today=marked_today,
                           total_students=total_students, at_risk=at_risk)


@teacher_bp.route('/mark-attendance', methods=['GET'])
@role_required('TEACHER')
def mark_attendance_page():
    teacher_id = session.get('user_id')
    user       = User.query.get(teacher_id)
    active_cls = _get_active_classroom(teacher_id)
    classrooms = _get_teacher_classrooms(teacher_id)

    if not active_cls:
        subjects = []
        students = []
    else:
        subjects = _get_classroom_subjects(teacher_id, active_cls.id)
        students = active_cls.students.filter_by(is_active=True).order_by(User.full_name).all()

    return render_template('teacher/mark_attendance.html',
                           user=user, classrooms=classrooms, active_cls=active_cls,
                           subjects=subjects, students=students,
                           today_date=date.today().isoformat())


@teacher_bp.route('/mark-attendance', methods=['POST'])
@role_required('TEACHER')
def mark_attendance():
    try:
        from datetime import date as date_type, datetime as datetime_type
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        student_id  = data.get('student_id')
        subject_id  = data.get('subject_id')
        status      = data.get('status', 'PRESENT')
        date_str    = data.get('date')
        if not student_id or not subject_id:
            return jsonify({'success': False, 'message': 'Missing student or subject'}), 400
        attendance_date = None
        if date_str:
            try:
                attendance_date = datetime_type.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid date format'}), 400
        attendance = AttendanceService.mark_attendance(
            student_id=student_id, subject_id=subject_id, status=status,
            marked_by=session.get('user_id'), confidence_score=1.0, is_manual=True,
            attendance_date=attendance_date)
        if attendance:
            student = User.query.get(student_id)
            return jsonify({'success': True,
                            'message': f'Attendance marked {status} for {student.full_name}',
                            'student_name': student.full_name})
        return jsonify({'success': False, 'message': 'Failed to mark attendance'}), 500
    except Exception as e:
        print(f"Error in mark_attendance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500



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


@teacher_bp.route('/class-attendance')
@role_required('TEACHER')
def class_attendance():
    teacher_id = session.get('user_id')
    user       = User.query.get(teacher_id)
    classrooms = _get_teacher_classrooms(teacher_id)
    active_cls = _get_active_classroom(teacher_id)

    subject_id = request.args.get('subject_id', type=int)
    date_str   = request.args.get('date')
    attendance_date = (datetime.strptime(date_str, '%Y-%m-%d').date()
                       if date_str else date.today())

    subjects = _get_classroom_subjects(teacher_id, active_cls.id) if active_cls else []

    if subject_id and active_cls:
        classroom_student_ids = [s.id for s in active_cls.students.filter_by(is_active=True).all()]
        all_records = AttendanceService.get_class_attendance(subject_id, attendance_date)
        records = [r for r in all_records if r.student_id in classroom_student_ids]
        selected_subject = Subject.query.get(subject_id)
    else:
        records = []
        selected_subject = None

    return render_template('teacher/class_attendance.html',
                           user=user, classrooms=classrooms, active_cls=active_cls,
                           subjects=subjects, selected_subject=selected_subject,
                           attendance_date=attendance_date, records=records)


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


@teacher_bp.route('/upload-marks')
@role_required('TEACHER')
def upload_marks_page():
    """Internal Marks upload page for teachers"""
    user = User.query.get(session.get('user_id'))
    return render_template('teacher/upload_marks.html', user=user)


@teacher_bp.route('/upload-marks', methods=['POST'])
@role_required('TEACHER')
def upload_marks():
    """Handle internal marks Excel/CSV upload"""
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

        result = ExcelService.import_internal_marks(filepath, uploaded_by=session.get('user_id'))

        import os
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


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
    """Manually enter internal mark for a student"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        student_id = data.get('student_id')
        subject_id = data.get('subject_id')
        exam_type = data.get('exam_type')
        marks = data.get('marks')
        max_marks = data.get('max_marks', 50.0)
        
        if not all([student_id, subject_id, exam_type, marks is not None]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        try:
            marks = float(marks)
            max_marks = float(max_marks)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid mark value'}), 400
            
        # Check existing
        existing = InternalMark.query.filter_by(
            student_id=student_id,
            subject_id=subject_id,
            exam_type=exam_type
        ).first()
        
        student = User.query.get(student_id)
        
        if existing:
            existing.marks_obtained = marks
            existing.max_marks = max_marks
            existing.uploaded_by = session.get('user_id')
            existing.uploaded_at = datetime.utcnow()
            message = f"Marks updated for {student.full_name}"
        else:
            mark = InternalMark(
                student_id=student_id,
                subject_id=subject_id,
                exam_type=exam_type,
                marks_obtained=marks,
                max_marks=max_marks,
                semester=student.semester,
                uploaded_by=session.get('user_id')
            )
            db.session.add(mark)
            message = f"Marks saved for {student.full_name}"
            
        db.session.commit()
        return jsonify({
            'success': True,
            'message': message,
            'student_name': student.full_name
        })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@teacher_bp.route('/api/marks', methods=['GET'])
@role_required('TEACHER')
def get_marks():
    """Fetch existing marks for a subject and exam type"""
    try:
        subject_id = request.args.get('subject_id')
        exam_type = request.args.get('exam_type')
        
        if not subject_id or not exam_type:
            return jsonify({'success': False, 'message': 'Missing parameters'}), 400
            
        marks = InternalMark.query.filter_by(
            subject_id=subject_id,
            exam_type=exam_type
        ).all()
        
        marks_dict = {mark.student_id: mark.marks_obtained for mark in marks}
        
        return jsonify({
            'success': True,
            'marks': marks_dict
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@teacher_bp.route('/ai-assistant')
@role_required('TEACHER')
def ai_assistant():
    """Teacher AI Assistant Interface"""
    user = User.query.get(session.get('user_id'))
    return render_template('teacher/ai_assistant.html', user=user)


@teacher_bp.route('/manage-faces')
@role_required('TEACHER')
def manage_faces():
    teacher_id = session.get('user_id')
    user       = User.query.get(teacher_id)
    active_cls = _get_active_classroom(teacher_id)
    students   = (active_cls.students.filter_by(is_active=True).order_by(User.full_name).all()
                  if active_cls else [])
    student_faces = []
    for s in students:
        encodings = s.face_encodings.all()
        student_faces.append({
            'student': s,
            'has_encoding': len(encodings) > 0,
            'encoding_count': len(encodings)
        })
    return render_template('teacher/manage_faces.html',
                           user=user, student_faces=student_faces, active_cls=active_cls)


@teacher_bp.route('/register-face/<int:student_id>')
@role_required('TEACHER')
def register_face(student_id):
    teacher_id = session.get('user_id')
    user       = User.query.get(teacher_id)
    student    = User.query.get_or_404(student_id)
    encodings  = student.face_encodings.all()
    return render_template('teacher/register_face.html',
                           user=user, student=student,
                           has_encoding=len(encodings) > 0,
                           encoding_count=len(encodings))


@teacher_bp.route('/add-face', methods=['POST'])
@role_required('TEACHER')
def add_face():
    try:
        from flask import current_app
        from services.face_recognition_service import get_face_service
        import os, uuid
        from PIL import Image

        data       = request.get_json()
        student_id = data.get('student_id')
        image_data = data.get('image')

        if not student_id or not image_data:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        face_service = get_face_service(current_app.config)
        image        = face_service.process_base64_image(image_data)

        if image is None:
            return jsonify({'success': False, 'message': 'Invalid image data'}), 400

        filename = f"user_{student_id}_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(current_app.config['FACE_IMAGES_FOLDER'], filename)
        Image.fromarray(image).save(filepath)

        face_enc = face_service.save_face_encoding(
            user_id=student_id, image=image, image_path=filename, is_primary=True)

        if face_enc:
            registered_user = User.query.get(student_id)
            return jsonify({'success': True,
                            'message': f'Face encoding saved for {registered_user.full_name}'})
        else:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'success': False,
                            'message': 'No face detected or multiple faces in image'}), 400
    except Exception as e:
        print(f"Error adding face: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
