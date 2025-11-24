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
    user = User.query.get(session.get('user_id'))
    
    # Get filter
    role_filter = request.args.get('role', 'all')
    
    if role_filter == 'all':
        users = User.query.all()
    else:
        users = User.query.filter_by(role=role_filter.upper()).all()
    
    context = {
        'user': user,
        'users': users,
        'role_filter': role_filter
    }
    
    return render_template('admin/manage_users.html', **context)


@admin_bp.route('/users/add', methods=['POST'])
@role_required('ADMIN')
def add_user():
    """Add new user"""
    try:
        data = request.form
        
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        full_name = data.get('full_name')
        role = data.get('role')
        student_id = data.get('student_id')
        department = data.get('department')
        semester = data.get('semester', type=int)
        
        # Validate
        if not all([username, password, email, full_name, role]):
            flash('All required fields must be filled', 'danger')
            return redirect(url_for('admin.manage_users'))
        
        # Check if username exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('admin.manage_users'))
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin.manage_users'))
        
        # Create user
        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role.upper(),
            student_id=student_id if role.upper() == 'STUDENT' else None,
            department=department,
            semester=semester if role.upper() == 'STUDENT' else None
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'User {full_name} added successfully', 'success')
        return redirect(url_for('admin.manage_users'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding user: {str(e)}', 'danger')
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
        
        subject_id = data.get('subject_id', type=int)
        day_of_week = data.get('day_of_week')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        room = data.get('room')
        semester = data.get('semester', type=int)
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
    """Manage student facial data"""
    user = User.query.get(session.get('user_id'))
    students = User.query.filter_by(role='STUDENT', is_active=True).all()
    
    # Check which students have face encodings
    student_faces = []
    for student in students:
        has_encoding = len(student.face_encodings.all()) > 0
        student_faces.append({
            'student': student,
            'has_encoding': has_encoding,
            'encoding_count': len(student.face_encodings.all())
        })
    
    context = {
        'user': user,
        'student_faces': student_faces
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
            student = User.query.get(student_id)
            return jsonify({
                'success': True,
                'message': f"Face encoding added for {student.full_name}"
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

