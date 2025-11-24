from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require specific role(s) for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if 'role' not in session or session['role'] not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    """Get current user from session"""
    from models.user import User
    
    if 'user_id' not in session:
        return None
    
    return User.query.get(session['user_id'])


def is_logged_in():
    """Check if user is logged in"""
    return 'user_id' in session


def is_student():
    """Check if current user is a student"""
    return session.get('role') == 'STUDENT'


def is_teacher():
    """Check if current user is a teacher"""
    return session.get('role') == 'TEACHER'


def is_admin():
    """Check if current user is an admin"""
    return session.get('role') == 'ADMIN'
