from flask import Blueprint, request, jsonify
from services.ai_service import get_ai_service

ai_bp = Blueprint('ai', __name__, url_prefix='/api')


@ai_bp.route('/ask_ai', methods=['POST'])
def ask_ai():
    """
    AI assistant endpoint
    
    Request JSON:
        {
            "question": "Who teaches Data Structures?"
        }
    
    Response JSON:
        {
            "answer": "Dr. Rajesh Kumar teaches Data Structures",
            "confidence": 0.92,
            "category": "faculty"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                'success': False,
                'error': 'No question provided'
            }), 400
        
        question = data['question'].strip()
        
        if not question:
            return jsonify({
                'success': False,
                'error': 'Question cannot be empty'
            }), 400
        
        # Get AI service
        from flask import current_app
        ai_service = get_ai_service(current_app.config)
        
        if not ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 503
        
        # Ask question — pass student_id so RAG includes personal attendance context
        from flask import session
        student_id = session.get('user_id') if session.get('role') == 'STUDENT' else None
        result = ai_service.ask(question, student_id=student_id)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        print(f"Error in ask_ai: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/ai_stats', methods=['GET'])
def ai_stats():
    """Get AI model statistics"""
    try:
        from flask import current_app
        ai_service = get_ai_service(current_app.config)
        
        if ai_service:
            stats = ai_service.get_stats()
            return jsonify({
                'success': True,
                **stats
            })
        else:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 503
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
