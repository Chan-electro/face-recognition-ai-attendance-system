from datetime import datetime
from models import db
import pickle


class FaceEncoding(db.Model):
    """Face encoding model for storing facial embeddings"""
    
    __tablename__ = 'face_encodings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    encoding_data = db.Column(db.LargeBinary, nullable=False)  # Pickled numpy array
    image_path = db.Column(db.String(255), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    is_primary = db.Column(db.Boolean, default=False)  # Primary encoding for matching
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship handled by User model backref
    
    def __repr__(self):
        return f'<FaceEncoding {self.user_id} - Primary: {self.is_primary}>'
    
    def set_encoding(self, encoding_array):
        """Store face encoding (numpy array) as pickled binary"""
        self.encoding_data = pickle.dumps(encoding_array)
    
    def get_encoding(self):
        """Retrieve face encoding as numpy array"""
        return pickle.loads(self.encoding_data)
    
    def to_dict(self):
        """Convert face encoding to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'image_path': self.image_path,
            'confidence_score': self.confidence_score,
            'is_primary': self.is_primary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
