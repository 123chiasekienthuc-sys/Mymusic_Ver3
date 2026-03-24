# application/controllers/exercise_controller.py
import json
import time
from flask import Blueprint, request, jsonify
from application.services.database_service import DatabaseService
from application.extensions import csrf
from difflib import SequenceMatcher

exercise_bp = Blueprint('exercise', __name__)
db = DatabaseService()


@exercise_bp.route('/exercises', methods=['GET'])
def get_exercises():
    """Lấy danh sách bài tập"""
    level = request.args.get('level')
    skill = request.args.get('skill')
    topic = request.args.get('topic')
    search = request.args.get('search')
    
    query = "SELECT * FROM exercises WHERE is_active = TRUE"
    params = []
    
    if level:
        query += " AND level = %s"
        params.append(level)
    if skill and skill != 'all':
        query += " AND skill = %s"
        params.append(skill)
    if topic and topic != 'all':
        query += " AND topic = %s"
        params.append(topic)
    if search:
        query += " AND (title LIKE %s OR code LIKE %s OR description LIKE %s)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    query += " ORDER BY level, code"
    
    result, error = db.execute_query(query, params if params else None)
    if error:
        return jsonify({"success": False, "error": error}), 500
    
    # Parse JSON fields
    for ex in result:
        if ex.get('requirements'):
            try:
                ex['requirements'] = json.loads(ex['requirements'])
            except:
                ex['requirements'] = []
    
    return jsonify({"success": True, "data": result})


@exercise_bp.route('/exercises/<code>', methods=['GET'])
def get_exercise(code):
    """Lấy chi tiết bài tập"""
    query = "SELECT * FROM exercises WHERE code = %s AND is_active = TRUE"
    result, error = db.execute_query(query, (code,), fetch_one=True)
    
    if error or not result:
        return jsonify({"success": False, "error": "Exercise not found"}), 404
    
    if result.get('requirements'):
        try:
            result['requirements'] = json.loads(result['requirements'])
        except:
            result['requirements'] = []
    
    return jsonify({"success": True, "data": result})


@exercise_bp.route('/exercises', methods=['POST'])
def create_exercise():
    """Thêm bài tập mới"""
    data = request.get_json()
    
    required_fields = ['code', 'level', 'title', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing field: {field}"}), 400
    
    requirements_json = json.dumps(data.get('requirements', []), ensure_ascii=False)
    
    query = """
        INSERT INTO exercises 
        (code, level, title, description, requirements, website_link, 
         hint, solution, explanation, default_query, skill, topic)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    params = (
        data['code'], data['level'], data['title'], data['description'],
        requirements_json, data.get('website_link'),
        data.get('hint'), data.get('solution'), data.get('explanation'),
        data.get('default_query'), data.get('skill'), data.get('topic')
    )
    
    _, error = db.execute_query(query, params)
    if error:
        return jsonify({"success": False, "error": error}), 500
    
    return jsonify({"success": True, "message": "Exercise created successfully"})


@exercise_bp.route('/exercises/<int:id>', methods=['PUT'])
def update_exercise(id):
    """Cập nhật bài tập"""
    data = request.get_json()
    
    requirements_json = json.dumps(data.get('requirements', []), ensure_ascii=False)
    
    query = """
        UPDATE exercises SET
        code=%s, level=%s, title=%s, description=%s, requirements=%s,
        website_link=%s, hint=%s, solution=%s, explanation=%s,
        default_query=%s, skill=%s, topic=%s
        WHERE id=%s
    """
    
    params = (
        data['code'], data['level'], data['title'], data['description'],
        requirements_json, data.get('website_link'),
        data.get('hint'), data.get('solution'), data.get('explanation'),
        data.get('default_query'), data.get('skill'), data.get('topic'),
        id
    )
    
    _, error = db.execute_query(query, params)
    if error:
        return jsonify({"success": False, "error": error}), 500
    
    return jsonify({"success": True, "message": "Exercise updated successfully"})


@exercise_bp.route('/exercises/<int:id>', methods=['DELETE'])
def delete_exercise(id):
    """Xóa bài tập (soft delete)"""
    query = "UPDATE exercises SET is_active = FALSE WHERE id = %s"
    _, error = db.execute_query(query, (id,))
    
    if error:
        return jsonify({"success": False, "error": error}), 500
    
    return jsonify({"success": True, "message": "Exercise deleted successfully"})


@exercise_bp.route('/check-sql', methods=['POST'])
@csrf.exempt
def check_sql():
    """Kiểm tra câu lệnh SQL của học sinh (thực thi thực tế)"""
    try:
        data = request.get_json()
        exercise_code = data.get('exercise_code')
        user_sql = data.get('sql', '').strip()
        
        if not user_sql:
            return jsonify({"success": False, "error": "Vui lòng nhập câu lệnh SQL"}), 400
        
        # Lấy thông tin bài tập
        ex_query = "SELECT * FROM exercises WHERE code = %s AND is_active = TRUE"
        exercise, error = db.execute_query(ex_query, (exercise_code,), fetch_one=True)
        
        if error or not exercise:
            return jsonify({"success": False, "error": "Exercise not found"}), 404
        
        # Chỉ cho phép SELECT
        if not user_sql.upper().strip().startswith('SELECT'):
            return jsonify({"success": False, "error": "Chỉ được phép thực thi câu lệnh SELECT"}), 400
        
        # Thực thi SQL
        start_time = time.time()
        user_result, user_error = db.execute_query(user_sql)
        execution_time = time.time() - start_time
        
        ip_address = request.remote_addr
        
        is_correct = False
        feedback = "Success"
        
        if user_error:
            is_correct = False
            feedback = user_error
        else:
            # So sánh với kết quả mẫu
            sample_result, sample_error = db.execute_query(exercise['solution'])
            if not sample_error and user_result == sample_result:
                is_correct = True
                feedback = "Chính xác! Câu lệnh SQL của bạn đúng."
            else:
                feedback = "Kết quả chưa chính xác. Hãy kiểm tra lại."
        
        # Lưu kết quả
        save_result_query = """
            INSERT INTO exercise_results 
            (exercise_id, user_sql, is_correct, feedback, execution_time, error_message, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        db.execute_query(save_result_query, (
            exercise['id'], user_sql, is_correct, feedback, 
            execution_time, user_error, ip_address
        ))
        
        return jsonify({
            "success": True,
            "is_correct": is_correct,
            "feedback": feedback,
            "execution_time": execution_time,
            "user_result": user_result if not user_error else None,
            "error": user_error
        })
        
    except Exception as e:
        print(f"Error in check_sql: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@exercise_bp.route('/grade-sql', methods=['POST'])
@csrf.exempt
def grade_sql():
    """Chấm điểm câu lệnh SQL (không thực thi)"""
    try:
        data = request.get_json()
        exercise_code = data.get('exercise_code')
        user_sql = data.get('sql', '').strip()
        
        if not user_sql:
            return jsonify({"success": False, "error": "Vui lòng nhập câu lệnh SQL"}), 400
        
        # Lấy bài tập
        ex_query = "SELECT * FROM exercises WHERE code = %s AND is_active = TRUE"
        exercise, error = db.execute_query(ex_query, (exercise_code,), fetch_one=True)
        
        if error or not exercise:
            return jsonify({"success": False, "error": "Không tìm thấy bài tập"}), 404
        
        # Chuẩn hóa SQL để so sánh
        def normalize_sql(sql):
            if not sql:
                return ""
            # Xóa khoảng trắng thừa, chuyển về chữ thường
            sql = ' '.join(sql.lower().split())
            # Thay dấu ngoặc kép bằng ngoặc đơn
            sql = sql.replace('"', "'")
            # Xóa dấu chấm phẩy cuối
            sql = sql.rstrip(';')
            return sql.strip()
        
        user_norm = normalize_sql(user_sql)
        correct_norm = normalize_sql(exercise['solution'])
        
        # Tính độ tương đồng
        similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
        score = round(similarity * 10, 1)
        
        # Đánh giá dựa trên độ tương đồng
        if similarity >= 0.95:
            is_correct = True
            feedback = "✅ Chính xác! Câu lệnh SQL của bạn rất tốt."
            improvement = ""
        elif similarity >= 0.8:
            is_correct = False
            feedback = "👍 Gần đúng! Câu lệnh của bạn gần với đáp án."
            improvement = "Kiểm tra lại cú pháp và thứ tự các câu lệnh."
        elif similarity >= 0.6:
            is_correct = False
            feedback = "📚 Tạm được. Còn một số phần chưa chính xác."
            improvement = "Xem lại phần JOIN và điều kiện WHERE."
        else:
            is_correct = False
            feedback = "❌ Chưa chính xác. Câu lệnh của bạn khác nhiều so với đáp án."
            improvement = "Hãy xem lại cấu trúc bảng và cách viết câu lệnh SELECT."
        
        return jsonify({
            "success": True,
            "is_correct": is_correct,
            "score": score,
            "feedback": feedback,
            "improvement": improvement,
            "similarity": similarity
        })
        
    except Exception as e:
        print(f"Error in grade_sql: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@exercise_bp.route('/exercise-stats', methods=['GET'])
def exercise_stats():
    """Thống kê bài tập"""
    query = """
        SELECT e.level, e.skill, e.topic, e.code, e.title,
               COUNT(DISTINCT er.id) as total_attempts,
               COALESCE(AVG(CASE WHEN er.is_correct THEN 1 ELSE 0 END) * 100, 0) as success_rate,
               COALESCE(AVG(er.execution_time), 0) as avg_execution_time
        FROM exercises e
        LEFT JOIN exercise_results er ON e.id = er.exercise_id
        WHERE e.is_active = TRUE
        GROUP BY e.id, e.level, e.skill, e.topic, e.code, e.title
        ORDER BY e.level, e.code
    """
    result, error = db.execute_query(query)
    
    if error:
        return jsonify({"success": False, "error": error}), 500
    
    return jsonify({"success": True, "data": result})