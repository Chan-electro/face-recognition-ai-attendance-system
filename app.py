from flask import Flask
from config import config
from models import db
from utils.db_utils import init_database, seed_database
import os


def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['FACE_IMAGES_FOLDER'], exist_ok=True)
    os.makedirs(app.config['AI_TRAINING_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EXPORTS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['AI_MODEL_PATH'], exist_ok=True)
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'database'), exist_ok=True)
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    from controllers.auth_controller import auth_bp
    from controllers.student_controller import student_bp
    from controllers.teacher_controller import teacher_bp
    from controllers.admin_controller import admin_bp
    from controllers.ai_controller import ai_bp
    from controllers.attendance_controller import attendance_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(attendance_bp)
    
    # Create database tables
    with app.app_context():
        init_database(app)
        seed_database(app)
    
    # Initialize AI service
    from services.ai_service import get_ai_service
    with app.app_context():
        ai_service = get_ai_service(app.config)
        if ai_service and not ai_service.is_trained:
            print("\nℹ️  AI model will be trained on first use or when admin triggers training.")
    
    # Initialize face recognition service
    from services.face_recognition_service import get_face_service
    with app.app_context():
        face_service = get_face_service(app.config)
        print("✓ Face recognition service initialized")
    
    print("\n" + "="*60)
    print("🎓 Face Recognition Attendance System Started!")
    print("="*60)
    print(f"Access the application at: http://localhost:5000")
    print("="*60 + "\n")
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
