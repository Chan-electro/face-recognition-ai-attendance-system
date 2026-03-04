import cv2
import numpy as np
import face_recognition
from PIL import Image
import io
import os
from models import db
from models.face_encoding import FaceEncoding
from models.user import User


class FaceRecognitionService:
    """Service for face detection, encoding, and recognition"""
    
    def __init__(self, detection_model='hog', tolerance=0.6):
        """
        Initialize face recognition service
        
        Args:
            detection_model: 'hog' for CPU (faster) or 'cnn' for GPU (more accurate)
            tolerance: Face matching tolerance (lower is more strict, default 0.6)
        """
        self.detection_model = detection_model
        self.tolerance = tolerance
        self.known_encodings = {}  # Cache of user_id -> encoding
        self.load_known_encodings()
    
    @staticmethod
    def _ensure_rgb(image):
        """Convert image to RGB format if needed (from BGR or other formats)"""
        if isinstance(image, np.ndarray) and len(image.shape) == 3:
            if image.shape[2] == 4:  # RGBA
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            elif image.shape[2] == 3:
                # Assume BGR from OpenCV and convert once
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image
    
    def load_known_encodings(self):
        """Load all known face encodings from database into cache"""
        try:
            encodings = FaceEncoding.query.filter_by(is_primary=True).all()
            self.known_encodings = {}
            
            for enc in encodings:
                self.known_encodings[enc.user_id] = enc.get_encoding()
            
            print(f"✓ Loaded {len(self.known_encodings)} face encodings into cache")
        except Exception as e:
            print(f"⚠ Error loading face encodings: {e}")
            self.known_encodings = {}
    
    def detect_faces(self, image):
        """
        Detect faces in an image
        
        Args:
            image: numpy array (RGB format expected)
            
        Returns:
            List of face locations [(top, right, bottom, left), ...]
        """
        try:
            # Detect face locations
            face_locations = face_recognition.face_locations(
                image,
                model=self.detection_model
            )
            
            return face_locations
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def encode_face(self, image, face_location=None):
        """
        Generate 128-D face encoding from image
        
        Args:
            image: numpy array (RGB format expected)
            face_location: Optional specific face location (top, right, bottom, left)
            
        Returns:
            numpy array of 128 dimensions or None if no face found
        """
        try:
            # Get face encodings
            if face_location:
                encodings = face_recognition.face_encodings(image, [face_location])
            else:
                encodings = face_recognition.face_encodings(image)
            
            if len(encodings) > 0:
                return encodings[0]
            
            return None
        except Exception as e:
            print(f"Error encoding face: {e}")
            return None
    
    def match_face(self, unknown_encoding):
        """
        Match an unknown face encoding against known encodings
        
        Args:
            unknown_encoding: 128-D face encoding numpy array
            
        Returns:
            dict with user_id, confidence, and match status
        """
        if not self.known_encodings:
            return {
                'matched': False,
                'user_id': None,
                'confidence': 0.0,
                'message': 'No registered faces in database'
            }
        
        # Get known encodings and user IDs
        known_user_ids = list(self.known_encodings.keys())
        known_face_encodings = list(self.known_encodings.values())
        
        # Calculate face distances (lower is better match)
        face_distances = face_recognition.face_distance(known_face_encodings, unknown_encoding)
        
        # Find best match
        best_match_index = np.argmin(face_distances)
        best_distance = face_distances[best_match_index]
        
        # Check if match is within tolerance
        if best_distance <= self.tolerance:
            confidence = 1.0 - best_distance  # Convert distance to confidence
            return {
                'matched': True,
                'user_id': known_user_ids[best_match_index],
                'confidence': float(confidence),
                'distance': float(best_distance),
                'message': 'Face matched successfully'
            }
        
        return {
            'matched': False,
            'user_id': None,
            'confidence': float(1.0 - best_distance),
            'distance': float(best_distance),
            'message': f'No match found (best distance: {best_distance:.3f})'
        }
    
    def save_face_encoding(self, user_id, image, image_path=None, is_primary=True):
        """
        Save face encoding to database
        
        Args:
            user_id: User ID
            image: numpy array or PIL Image
            image_path: Optional path where image is stored
            is_primary: Whether this is the primary encoding for matching
            
        Returns:
            FaceEncoding object or None if failed
        """
        try:
            # Ensure image is in RGB format
            image = self._ensure_rgb(image)
            
            # Detect faces
            face_locations = self.detect_faces(image)
            
            if len(face_locations) == 0:
                print("No face detected in image")
                return None
            
            if len(face_locations) > 1:
                print(f"Warning: Multiple faces detected ({len(face_locations)}), using first one")
            
            # Encode face
            encoding = self.encode_face(image, face_locations[0])
            
            if encoding is None:
                print("Failed to encode face")
                return None
            
            # If this is primary, unset other primary encodings for this user
            if is_primary:
                FaceEncoding.query.filter_by(user_id=user_id, is_primary=True).update({'is_primary': False})
            
            # Create face encoding record
            face_enc = FaceEncoding(
                user_id=user_id,
                image_path=image_path,
                is_primary=is_primary,
                confidence_score=0.95  # Initial confidence
            )
            face_enc.set_encoding(encoding)
            
            db.session.add(face_enc)
            db.session.commit()
            
            # Update cache if primary
            if is_primary:
                self.known_encodings[user_id] = encoding
            
            print(f"✓ Face encoding saved for user {user_id}")
            return face_enc
            
        except Exception as e:
            print(f"Error saving face encoding: {e}")
            db.session.rollback()
            return None
    
    def recognize_from_image(self, image):
        """
        Complete face recognition from image
        
        Args:
            image: numpy array or PIL Image
            
        Returns:
            dict with recognition results
        """
        try:
            # Ensure image is in RGB format
            image = self._ensure_rgb(image)
            
            # Detect faces
            face_locations = self.detect_faces(image)
            
            if len(face_locations) == 0:
                return {
                    'success': False,
                    'message': 'No face detected in image',
                    'faces_detected': 0
                }
            
            # Use first detected face
            face_location = face_locations[0]
            
            # Encode face
            encoding = self.encode_face(image, face_location)
            
            if encoding is None:
                return {
                    'success': False,
                    'message': 'Failed to encode detected face',
                    'faces_detected': len(face_locations)
                }
            
            # Match face
            match_result = self.match_face(encoding)
            
            result = {
                'success': match_result['matched'],
                'faces_detected': len(face_locations),
                'face_location': face_location,
                **match_result
            }
            
            # Add user details if matched
            if match_result['matched']:
                user = User.query.get(match_result['user_id'])
                if user:
                    result['user'] = user.to_dict()
            
            return result
            
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'faces_detected': 0
            }
    
    def process_base64_image(self, base64_string):
        """
        Process base64 encoded image for face recognition
        
        Args:
            base64_string: Base64 encoded image string
            
        Returns:
            numpy array image
        """
        import base64
        
        try:
            # Remove data URL prefix if present
            if 'base64,' in base64_string:
                base64_string = base64_string.split('base64,')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_string)
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to numpy array
            image_array = np.array(image)
            
            return image_array
            
        except Exception as e:
            print(f"Error processing base64 image: {e}")
            return None


# Global face recognition service instance
_face_service = None


def get_face_service(config=None):
    """Get or create face recognition service singleton"""
    global _face_service
    
    if _face_service is None and config:
        _face_service = FaceRecognitionService(
            detection_model=config['FACE_DETECTION_MODEL'],
            tolerance=config['FACE_RECOGNITION_TOLERANCE']
        )
    
    return _face_service
