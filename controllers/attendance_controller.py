from flask import Blueprint, render_template, request, jsonify, session
from utils.auth_utils import role_required
from models.user import User
from models.subject import Subject
from services.attendance_service import AttendanceService
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


@attendance_bp.route('/mark-face', methods=['POST'])
@role_required('TEACHER')
def mark_attendance_face():
    """Mark attendance using face recognition"""
    try:
        # Get image from request
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'message': 'No image data provided'}), 400
            
        subject_id = data.get('subject_id')
        if not subject_id:
            return jsonify({'success': False, 'message': 'Subject ID required'}), 400
        
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
            student_id = user_data['id']
            student = User.query.get(student_id)
            
            if student.role != 'STUDENT':
                return jsonify({'success': False, 'message': 'Recognized face is not a student'}), 400
            
            # Mark attendance
            marker_id = session.get('user_id')
            attendance_record = AttendanceService.mark_attendance(
                student_id=student_id,
                subject_id=subject_id,
                status='PRESENT',
                date=datetime.now().date(),
                marked_by=marker_id
            )
            
            if attendance_record:
                return jsonify({
                    'success': True,
                    'message': f'Attendance marked for {student.full_name}',
                    'student': {
                        'name': student.full_name,
                        'student_id': student.student_id
                    }
                })
            else:
                return jsonify({'success': False, 'message': 'Failed to mark attendance'}), 500
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Face not recognized')
            }), 400
            
    except Exception as e:
        print(f"Error marking attendance: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
