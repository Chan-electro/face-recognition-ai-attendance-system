import os
from werkzeug.utils import secure_filename
from flask import current_app


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'csv', 'txt', 'pdf'}


def allowed_file(filename, allowed_exts=None):
    """Check if file extension is allowed"""
    if allowed_exts is None:
        allowed_exts = ALLOWED_EXTENSIONS
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_exts


def save_uploaded_file(file, folder_name):
    """Save uploaded file to specified folder"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Create unique filename if file exists
        base_name, extension = os.path.splitext(filename)
        counter = 1
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_name)
        
        # Ensure folder exists
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        while os.path.exists(filepath):
            filename = f"{base_name}_{counter}{extension}"
            filepath = os.path.join(upload_folder, filename)
            counter += 1
        
        file.save(filepath)
        return filepath
    
    return None


def delete_file(filepath):
    """Delete file if it exists"""
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def ensure_dir_exists(directory):
    """Ensure directory exists, create if it doesn't"""
    os.makedirs(directory, exist_ok=True)
