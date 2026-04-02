# application/controllers/ai_controller.py
import os
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from application.services.database_service import DatabaseService
from application.extensions import csrf

ai_bp = Blueprint('ai', __name__)  # Dòng này PHẢI CÓ ở đầu file
db = DatabaseService()
logger = logging.getLogger(__name__)

# Import AI Assistant
try:
    from ai_assistant import sql_assistant
    AI_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ AI Assistant not available")
    AI_AVAILABLE = False


@ai_bp.route('/thuc-hanh-ai', methods=['GET'])
def thuc_hanh_ai():
    """Trang thực hành SQL với AI"""
    return render_template('thuc_hanh_ai.html')


# Thêm route redirect để hỗ trợ cả hai URL
@ai_bp.route('/ai/thuc-hanh-ai', methods=['GET'])
def thuc_hanh_ai_redirect():
    """Redirect từ /ai/thuc-hanh-ai sang /thuc-hanh-ai"""
    return redirect(url_for('ai.thuc_hanh_ai', **request.args))


@ai_bp.route('/chat', methods=['POST'])
@csrf.exempt
def ai_chat():
    """API chat với AI"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Không có dữ liệu'}), 400
        
        message = data.get('message', '').strip()
        context = data.get('context', '')
        
        if not message:
            return jsonify({'success': False, 'error': 'Vui lòng nhập câu hỏi'}), 400
        
        if not AI_AVAILABLE:
            return jsonify({
                'success': True,
                'response': "Xin lỗi, tính năng AI hiện không khả dụng. Vui lòng thử lại sau."
            })
        
        response = sql_assistant.chat_response(message, context)
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        logger.error(f"Error in ai_chat: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_bp.route('/generate-exercise', methods=['POST'])
@csrf.exempt
def generate_exercise():
    """API tạo bài tập mới"""
    try:
        data = request.get_json() or {}
        topic = data.get('topic', '')
        
        if not AI_AVAILABLE:
            return jsonify({
                'title': f'Bài tập về {topic}',
                'description': f'Thực hành SQL chủ đề {topic}',
                'solution': 'SELECT * FROM bannhac',
                'hint': 'Thử nghiệm với SELECT'
            })
        
        exercise = sql_assistant.generate_exercise(topic)
        return jsonify(exercise)
        
    except Exception as e:
        logger.error(f"Error generating exercise: {e}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/validate-sql', methods=['POST'])
@csrf.exempt
def validate_sql():
    """API kiểm tra cú pháp SQL"""
    try:
        data = request.get_json()
        sql = data.get('sql', '').strip()
        
        if not sql:
            return jsonify({"valid": False, "error": "Câu lệnh SQL trống"})
        
        # Kiểm tra cú pháp bằng EXPLAIN
        result, error = db.execute_query(f"EXPLAIN {sql}")
        
        if error:
            return jsonify({"valid": False, "error": f"Lỗi cú pháp: {error}"})
        
        return jsonify({"valid": True, "message": "Cú pháp SQL hợp lệ"})
        
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})


@ai_bp.route('/execute-sql', methods=['POST'])
@csrf.exempt
def execute_sql():
    """API thực thi SQL an toàn"""
    try:
        data = request.get_json()
        sql = data.get('sql', '').strip()
        
        if not sql:
            return jsonify({"success": False, "error": "Vui lòng nhập câu lệnh SQL"})
        
        # Chỉ cho phép SELECT
        if not sql.strip().upper().startswith('SELECT'):
            return jsonify({"success": False, "error": "Chỉ được phép thực thi câu lệnh SELECT"})
        
        result, error = db.execute_query(sql)
        if error:
            return jsonify({"success": False, "error": error})
        
        return jsonify({"success": True, "data": result, "count": len(result) if result else 0})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})