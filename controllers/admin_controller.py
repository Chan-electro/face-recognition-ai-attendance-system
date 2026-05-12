from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from utils.auth_utils import role_required
from models import db
from models.user import User
from models.subject import Subject
from models.faculty import Faculty
from models.timetable import Timetable
from services.ai_service import get_ai_service
from datetime import datetime, time
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@role_required('ADMIN')
def dashboard():
    """Admin dashboard"""
    user = User.query.get(session.get('user_id'))
    
    # Get statistics
    total_students = User.query.filter_by(role='STUDENT', is_active=True).count()
    total_teachers = User.query.filter_by(role='TEACHER', is_active=True).count()
    total_subjects = Subject.query.filter_by(is_active=True).count()
    total_faculty = Faculty.query.filter_by(is_active=True).count()
    
    # Get AI stats
    from flask import current_app
    ai_service = get_ai_service(current_app.config)
    ai_stats = ai_service.get_stats() if ai_service else {'is_trained': False}
    
    context = {
        'user': user,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_subjects': total_subjects,
        'total_faculty': total_faculty,
        'ai_stats': ai_stats
    }
    
    return render_template('admin/dashboard.html', **context)


@admin_bp.route('/users')
@role_required('ADMIN')
def manage_users():
    """Manage users"""
    from models.classroom import Classroom
    user = User.query.get(session.get('user_id'))
    role_filter = request.args.get('role', 'all')
    if role_filter == 'all':
        users = User.query.all()
    else:
        users = User.query.filter_by(role=role_filter.upper()).all()
    classrooms = Classroom.query.filter_by(is_active=True).order_by(Classroom.name).all()
    subjects   = Subject.query.filter_by(is_active=True).order_by(Subject.code).all()
    context = {
        'user': user,
        'users': users,
        'role_filter': role_filter,
        'classrooms': classrooms,
        'subjects': subjects,
    }
    return render_template('admin/manage_users.html', **context)


@admin_bp.route('/users/add', methods=['POST'])
@role_required('ADMIN')
def add_user():
    """Add new user (supports both form and AJAX)"""
    is_ajax = request.content_type and 'json' in request.content_type
    try:
        if is_ajax:
            data = request.get_json()
        else:
            data = request.form

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()
        full_name = data.get('full_name', '').strip()
        role = data.get('role', '').strip()
        student_id = data.get('student_id', '').strip()
        department = data.get('department', '').strip()
        section = data.get('section', '').strip()
        semester_raw = data.get('semester')
        semester = int(semester_raw) if semester_raw and str(semester_raw).strip().isdigit() else None

        # Validate
        if not all([username, password, email, full_name, role]):
            msg = 'All required fields must be filled'
            if is_ajax:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('admin.manage_users'))

        # Check if username exists
        if User.query.filter_by(username=username).first():
            msg = f'Username "{username}" already exists'
            if is_ajax:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('admin.manage_users'))

        # Check if email exists
        if User.query.filter_by(email=email).first():
            msg = f'Email "{email}" already exists'
            if is_ajax:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('admin.manage_users'))

        # Check student_id uniqueness
        if role.upper() == 'STUDENT' and student_id:
            if User.query.filter_by(student_id=student_id).first():
                msg = f'Student ID "{student_id}" already exists'
                if is_ajax:
                    return jsonify({'success': False, 'message': msg}), 400
                flash(msg, 'danger')
                return redirect(url_for('admin.manage_users'))

        classroom_id_raw = data.get('classroom_id')
        classroom_id = int(classroom_id_raw) if role.upper() == 'STUDENT' and classroom_id_raw else None

        # Create user
        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role.upper(),
            student_id=student_id if role.upper() == 'STUDENT' else None,
            department=department if department else None,
            semester=semester if role.upper() == 'STUDENT' else None,
            section=section if role.upper() == 'STUDENT' and section else None,
            classroom_id=classroom_id,
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Sync semester/section from classroom if assigned
        if new_user.role == 'STUDENT' and new_user.classroom_id:
            from models.classroom import Classroom
            cls = Classroom.query.get(new_user.classroom_id)
            if cls:
                new_user.semester = cls.semester
                new_user.section  = cls.section
                db.session.commit()

        # Create teacher-subject assignments across all active classrooms
        if new_user.role == 'TEACHER':
            raw_ids = data.get('subject_ids', [])
            if isinstance(raw_ids, (str, int)):
                raw_ids = [raw_ids]
            subject_ids = []
            for sid in raw_ids:
                try:
                    subject_ids.append(int(sid))
                except (ValueError, TypeError):
                    pass
            if subject_ids:
                from models.teacher_assignment import TeacherAssignment
                from models.classroom import Classroom
                classrooms = Classroom.query.filter_by(is_active=True).all()
                for cls in classrooms:
                    for sid in subject_ids:
                        exists = TeacherAssignment.query.filter_by(
                            teacher_id=new_user.id,
                            classroom_id=cls.id,
                            subject_id=sid
                        ).first()
                        if not exists:
                            db.session.add(TeacherAssignment(
                                teacher_id=new_user.id,
                                classroom_id=cls.id,
                                subject_id=sid
                            ))
                db.session.commit()

        msg = f'User {full_name} added successfully'
        if is_ajax:
            return jsonify({'success': True, 'message': msg, 'user': new_user.to_dict()})
        flash(msg, 'success')
        return redirect(url_for('admin.manage_users'))

    except Exception as e:
        db.session.rollback()
        msg = f'Error adding user: {str(e)}'
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 500
        flash(msg, 'danger')
        return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@role_required('ADMIN')
def delete_user(user_id):
    """Delete user (soft delete - mark as inactive)"""
    try:
        user_to_delete = User.query.get(user_id)
        
        if not user_to_delete:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Prevent deleting self
        if user_to_delete.id == session.get('user_id'):
            return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
        
        # Soft delete
        user_to_delete.is_active = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'User {user_to_delete.full_name} deactivated'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/timetable')
@role_required('ADMIN')
def manage_timetable():
    """Manage timetable"""
    user = User.query.get(session.get('user_id'))
    
    # Get all timetable entries
    entries = Timetable.query.order_by(Timetable.day_of_week, Timetable.start_time).all()
    
    # Get subjects for dropdown
    subjects = Subject.query.filter_by(is_active=True).all()
    
    # Organize by day
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']
    schedule = {day: [] for day in days}
    
    for entry in entries:
        if entry.is_active and entry.day_of_week in schedule:
            schedule[entry.day_of_week].append(entry)
    
    context = {
        'user': user,
        'schedule': schedule,
        'days': days,
        'subjects': subjects
    }
    
    return render_template('admin/manage_timetable.html', **context)


@admin_bp.route('/timetable/add', methods=['POST'])
@role_required('ADMIN')
def add_timetable_entry():
    """Add timetable entry"""
    try:
        data = request.form
        
        subject_id = int(data.get('subject_id')) if data.get('subject_id') else None
        day_of_week = data.get('day_of_week')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        room = data.get('room')
        semester = int(data.get('semester')) if data.get('semester') else None
        department = data.get('department')
        
        # Validate
        if not all([subject_id, day_of_week, start_time_str, end_time_str]):
            flash('All required fields must be filled', 'danger')
            return redirect(url_for('admin.manage_timetable'))
        
        # Parse times
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Create entry
        entry = Timetable(
            subject_id=subject_id,
            day_of_week=day_of_week.upper(),
            start_time=start_time,
            end_time=end_time,
            room=room,
            semester=semester,
            department=department
        )
        
        db.session.add(entry)
        db.session.commit()
        
        flash('Timetable entry added successfully', 'success')
        return redirect(url_for('admin.manage_timetable'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding timetable entry: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_timetable'))


@admin_bp.route('/timetable/<int:entry_id>/delete', methods=['POST'])
@role_required('ADMIN')
def delete_timetable_entry(entry_id):
    """Delete timetable entry"""
    try:
        entry = Timetable.query.get(entry_id)
        
        if not entry:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404
        
        db.session.delete(entry)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Timetable entry deleted'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/ai-training')
@role_required('ADMIN')
def ai_training():
    """AI training data management"""
    user = User.query.get(session.get('user_id'))
    
    # Get AI stats
    from flask import current_app
    ai_service = get_ai_service(current_app.config)
    ai_stats = ai_service.get_stats() if ai_service else None
    
    # Check if training data files exist
    training_folder = current_app.config['AI_TRAINING_FOLDER']
    files = []
    
    if os.path.exists(training_folder):
        for filename in os.listdir(training_folder):
            filepath = os.path.join(training_folder, filename)
            if os.path.isfile(filepath):
                files.append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath))
                })
    
    context = {
        'user': user,
        'ai_stats': ai_stats,
        'training_files': files
    }
    
    return render_template('admin/ai_training.html', **context)


@admin_bp.route('/ai-training/upload', methods=['POST'])
@role_required('ADMIN')
def upload_training_data():
    """Upload AI training data file"""
    try:
        if 'file' not in request.files:
            flash('No file provided', 'danger')
            return redirect(url_for('admin.ai_training'))
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('admin.ai_training'))
        
        # Save file
        from utils.file_utils import save_uploaded_file
        filepath = save_uploaded_file(file, 'ai_training')
        
        if filepath:
            flash(f'File {file.filename} uploaded successfully', 'success')
        else:
            flash('Failed to upload file', 'danger')
        
        return redirect(url_for('admin.ai_training'))
        
    except Exception as e:
        flash(f'Error uploading file: {str(e)}', 'danger')
        return redirect(url_for('admin.ai_training'))


@admin_bp.route('/ai-training/retrain', methods=['POST'])
@role_required('ADMIN')
def retrain_ai():
    """Retrain AI model"""
    try:
        from flask import current_app
        ai_service = get_ai_service(current_app.config)
        
        if ai_service:
            # Train model
            success = ai_service.train(current_app.config['AI_TRAINING_FOLDER'])
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'AI model retrained successfully',
                    'stats': ai_service.get_stats()
                })
            else:
                return jsonify({'success': False, 'message': 'Training failed'}), 500
        else:
            return jsonify({'success': False, 'message': 'AI service not available'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/subjects')
@role_required('ADMIN')
def manage_subjects():
    """Manage subjects"""
    user = User.query.get(session.get('user_id'))
    subjects = Subject.query.all()
    faculties = Faculty.query.filter_by(is_active=True).all()
    
    context = {
        'user': user,
        'subjects': subjects,
        'faculties': faculties
    }
    
    return render_template('admin/manage_subjects.html', **context)


@admin_bp.route('/faculty')
@role_required('ADMIN')
def manage_faculty():
    """Manage faculty"""
    user = User.query.get(session.get('user_id'))
    faculties = Faculty.query.all()
    
    context = {
        'user': user,
        'faculties': faculties
    }
    
    return render_template('admin/manage_faculty.html', **context)


@admin_bp.route('/manage-faces')
@role_required('ADMIN')
def manage_faces():
    """Manage student and teacher facial data"""
    user = User.query.get(session.get('user_id'))
    # Fetch both Students and Teachers for face registration
    users_for_faces = User.query.filter(User.role.in_(['STUDENT', 'TEACHER', 'ADMIN']), User.is_active==True).all()
    
    # Check which users have face encodings
    user_faces = []
    for u in users_for_faces:
        encodings = u.face_encodings.all()
        user_faces.append({
            'user': u,
            'has_encoding': len(encodings) > 0,
            'encoding_count': len(encodings)
        })
    
    context = {
        'user': user,
        'user_faces': user_faces
    }
    
    return render_template('admin/manage_faces.html', **context)


@admin_bp.route('/add-face', methods=['POST'])
@role_required('ADMIN')
def add_face():
    """Add face encoding for a student"""
    try:
        data = request.get_json()
        
        student_id = data.get('student_id')
        image_data = data.get('image')
        
        if not student_id or not image_data:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Get face recognition service
        from flask import current_app
        from services.face_recognition_service import get_face_service
        face_service = get_face_service(current_app.config)
        
        # Process image
        image = face_service.process_base64_image(image_data)
        
        if image is None:
            return jsonify({'success': False, 'message': 'Invalid image data'}), 400
        
        # Save face encoding
        import os
        import uuid
        
        filename = f"user_{student_id}_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(current_app.config['FACE_IMAGES_FOLDER'], filename)
        
        # Save original image
        from PIL import Image
        img_obj = Image.fromarray(image)
        img_obj.save(filepath)
        
        # Generate and save encoding
        face_enc = face_service.save_face_encoding(
            user_id=student_id,
            image=image,
            image_path=filename,
            is_primary=True
        )
        
        if face_enc:
            registered_user = User.query.get(student_id)
            return jsonify({
                'success': True,
                'message': f"Face encoding added for {registered_user.full_name}"
            })
        else:
            # Clean up file if encoding failed
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                'success': False,
                'message': 'Failed to detect face or multiple faces detected'
            }), 400
            
    except Exception as e:
        print(f"Error adding face: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/upload-excel')
@role_required('ADMIN')
def upload_excel_page():
    """Excel upload page"""
    user = User.query.get(session.get('user_id'))
    return render_template('admin/upload_excel.html', user=user)


@admin_bp.route('/upload-excel', methods=['POST'])
@role_required('ADMIN')
def upload_excel():
    """Handle Excel/CSV file upload for bulk import"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400

        file = request.files['file']
        upload_type = request.form.get('upload_type', 'attendance')

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        # Save file temporarily
        from utils.file_utils import save_uploaded_file
        filepath = save_uploaded_file(file, 'exports')

        if not filepath:
            return jsonify({'success': False, 'message': 'Invalid file type. Use .xlsx, .xls, or .csv'}), 400

        # Process based on type
        from services.excel_service import ExcelService
        user_id = session.get('user_id')

        if upload_type == 'attendance':
            result = ExcelService.import_attendance(filepath, uploaded_by=user_id)
        elif upload_type == 'marks':
            result = ExcelService.import_internal_marks(filepath, uploaded_by=user_id)
        elif upload_type == 'students':
            result = ExcelService.import_students(filepath)
        else:
            result = {'success': False, 'message': 'Invalid upload type'}

        # Clean up temp file
        try:
            os.remove(filepath)
        except OSError:
            pass

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


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


@admin_bp.route('/classrooms/<int:cls_id>')
@role_required('ADMIN')
def classroom_detail(cls_id):
    from models.classroom import Classroom
    from models.teacher_assignment import TeacherAssignment
    user = User.query.get(session.get('user_id'))
    cls = Classroom.query.get_or_404(cls_id)
    students    = cls.students.filter_by(is_active=True).order_by(User.full_name).all()
    unassigned  = User.query.filter_by(role='STUDENT', is_active=True, classroom_id=None).order_by(User.full_name).all()
    assignments = TeacherAssignment.query.filter_by(classroom_id=cls_id).all()
    teachers    = User.query.filter_by(role='TEACHER', is_active=True).order_by(User.full_name).all()
    subjects    = Subject.query.filter_by(is_active=True).order_by(Subject.code).all()
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
