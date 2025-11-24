from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db
from models.user import User
from utils.auth_utils import login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    # Redirect if already logged in
    if 'user_id' in session:
        role = session.get('role')
        if role == 'STUDENT':
            return redirect(url_for('student.dashboard'))
        elif role == 'TEACHER':
            return redirect(url_for('teacher.dashboard'))
        elif role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        # Validate input
        if not username or not password:
            flash('Please enter both username and password', 'danger')
            return render_template('login.html')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        # Check credentials
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact administrator.', 'warning')
                return render_template('login.html')
            
            # Set session
            session.permanent = bool(remember)
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['role'] = user.role
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            # Redirect based on role
            if user.role == 'STUDENT':
                return redirect(url_for('student.dashboard'))
            elif user.role == 'TEACHER':
                return redirect(url_for('teacher.dashboard'))
            elif user.role == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    username = session.get('full_name', 'User')
    session.clear()
    flash(f'Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/')
def index():
    """Root redirect to login or dashboard"""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'STUDENT':
            return redirect(url_for('student.dashboard'))
        elif role == 'TEACHER':
            return redirect(url_for('teacher.dashboard'))
        elif role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
    
    return redirect(url_for('auth.login'))


@auth_bp.route('/login-with-face', methods=['POST'])
def login_with_face():
    """Login using face recognition"""
    try:
        # Get image from request
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'message': 'No image data provided'}), 400
        
        image_data = data['image']
        
        # Initialize face service
        from services.face_recognition_service import get_face_service
        from flask import current_app
        face_service = get_face_service(current_app.config)
        
        # Process image
        image = face_service.process_base64_image(image_data)
        if image is None:
            return jsonify({'success': False, 'message': 'Invalid image data'}), 400
        
        # Recognize face
        result = face_service.recognize_from_image(image)
        
        if result['success'] and result['user']:
            user_data = result['user']
            user = User.query.get(user_data['id'])
            
            if not user.is_active:
                return jsonify({'success': False, 'message': 'Account deactivated'}), 403
            
            # Set session
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['role'] = user.role
            
            # Determine redirect URL
            redirect_url = url_for('student.dashboard')
            if user.role == 'TEACHER':
                redirect_url = url_for('teacher.dashboard')
            elif user.role == 'ADMIN':
                redirect_url = url_for('admin.dashboard')
                
            return jsonify({
                'success': True,
                'message': f'Welcome back, {user.full_name}!',
                'redirect_url': redirect_url
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Face not recognized')
            }), 401
            
    except Exception as e:
        print(f"Error in face login: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
