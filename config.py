import os
from datetime import timedelta

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration"""
    
    # Flask settings
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'database', 'attendance.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data')
    FACE_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'face_images')
    AI_TRAINING_FOLDER = os.path.join(UPLOAD_FOLDER, 'ai_training')
    EXPORTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'exports')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # AI Model settings
    AI_MODEL_NAME = 'all-MiniLM-L6-v2'
    AI_MODEL_PATH = os.path.join(BASE_DIR, 'ai_models')
    AI_EMBEDDINGS_FILE = os.path.join(AI_MODEL_PATH, 'qa_embeddings.pkl')
    AI_CONFIDENCE_THRESHOLD = 0.5
    
    # Face Recognition settings
    FACE_DETECTION_MODEL = 'hog'  # 'hog' for CPU, 'cnn' for GPU
    FACE_RECOGNITION_TOLERANCE = 0.6  # Lower is more strict
    FACE_ENCODING_MODEL = 'large'  # 'small' or 'large'
    
    # Attendance settings
    MINIMUM_ATTENDANCE_PERCENTAGE = 75
    LATE_THRESHOLD_MINUTES = 10
    
    # Application settings
    ENABLE_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
