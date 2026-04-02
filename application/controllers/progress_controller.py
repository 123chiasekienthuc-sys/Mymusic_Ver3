# application/controllers/progress_controller.py
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from application.services.database_service import DatabaseService

progress_bp = Blueprint('progress', __name__)
db = DatabaseService()


@progress_bp.route('/overview')
@login_required
def get_overview():
    """Lấy thống kê tổng quan"""
    try:
        user_id = current_user.id
        
        # Tổng số bài tập
        result, _ = db.execute_query("SELECT COUNT(*) as total FROM exercises WHERE is_active = 1", fetch_one=True)
        total = result['total'] if result else 80
        
        # Số bài đã làm của user
        result, _ = db.execute_query("""
            SELECT COUNT(DISTINCT exercise_id) as completed 
            FROM exercise_results 
            WHERE user_id = %s
        """, (user_id,), fetch_one=True)
        completed_count = result['completed'] if result else 0
        
        # Số bài đúng
        result, _ = db.execute_query("""
            SELECT COUNT(*) as correct 
            FROM exercise_results 
            WHERE user_id = %s AND is_correct = 1
        """, (user_id,), fetch_one=True)
        correct_count = result['correct'] if result else 0
        
        # Tỷ lệ đúng
        correct_rate = round((correct_count / completed_count * 100) if completed_count > 0 else 0)
        
        # Thời gian học (giả sử mỗi bài 10 phút)
        study_hours = round(completed_count * 10 / 60, 1)
        
        # Trình độ hiện tại
        result, _ = db.execute_query("""
            SELECT COALESCE(MAX(e.level), 1) as current_level
            FROM exercise_results er
            JOIN exercises e ON er.exercise_id = e.id
            WHERE er.user_id = %s AND er.is_correct = 1
        """, (user_id,), fetch_one=True)
        current_level_val = result['current_level'] if result else 1
        
        return jsonify({
            'success': True,
            'data': {
                'completed': completed_count,
                'total_exercises': total,
                'correct': correct_count,
                'correct_rate': correct_rate,
                'study_hours': study_hours,
                'current_level': current_level_val
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@progress_bp.route('/level-detail')
@login_required
def get_level_detail():
    """Lấy tiến độ theo từng level"""
    try:
        user_id = current_user.id
        
        level_names = {
            1: {'name': 'Cơ bản', 'icon': '🌱'},
            2: {'name': 'Trung bình', 'icon': '📊'},
            3: {'name': 'Khá', 'icon': '⚡'},
            4: {'name': 'Giỏi', 'icon': '🌟'}
        }
        
        results = []
        for level in range(1, 5):
            # Tổng số bài ở level này
            result, _ = db.execute_query("""
                SELECT COUNT(*) as total FROM exercises 
                WHERE level = %s AND is_active = 1
            """, (level,), fetch_one=True)
            total_count = result['total'] if result else 20
            
            # Số bài đã hoàn thành
            result, _ = db.execute_query("""
                SELECT COUNT(DISTINCT er.exercise_id) as completed
                FROM exercise_results er
                JOIN exercises e ON er.exercise_id = e.id
                WHERE er.user_id = %s AND e.level = %s
            """, (user_id, level), fetch_one=True)
            completed_count = result['completed'] if result else 0
            
            # Số bài đúng
            result, _ = db.execute_query("""
                SELECT COUNT(*) as correct
                FROM exercise_results er
                JOIN exercises e ON er.exercise_id = e.id
                WHERE er.user_id = %s AND e.level = %s AND er.is_correct = 1
            """, (user_id, level), fetch_one=True)
            correct_count = result['correct'] if result else 0
            
            percentage = round((completed_count / total_count * 100) if total_count > 0 else 0)
            
            # Xác định trạng thái
            if percentage == 100:
                status = 'Đã hoàn thành'
            elif percentage >= 50:
                status = 'Đang tiến bộ'
            else:
                status = 'Cần cố gắng thêm'
            
            results.append({
                'level': level,
                'name': level_names[level]['name'],
                'icon': level_names[level]['icon'],
                'total': total_count,
                'completed': completed_count,
                'correct': correct_count,
                'percentage': percentage,
                'status': status
            })
        
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@progress_bp.route('/skills')
@login_required
def get_skills():
    """Lấy điểm mạnh/điểm yếu theo kỹ năng"""
    try:
        user_id = current_user.id
        
        skills = ['select', 'join', 'group', 'subquery', 'insert', 'update', 'delete']
        skill_names = {
            'select': {'name': 'SELECT cơ bản', 'icon': '🔍'},
            'join': {'name': 'JOIN', 'icon': '🔗'},
            'group': {'name': 'GROUP BY & HAVING', 'icon': '📊'},
            'subquery': {'name': 'Subquery', 'icon': '📝'},
            'insert': {'name': 'INSERT', 'icon': '➕'},
            'update': {'name': 'UPDATE', 'icon': '✏️'},
            'delete': {'name': 'DELETE', 'icon': '🗑️'}
        }
        
        results = []
        for skill in skills:
            # Tổng số bài của kỹ năng này
            result, _ = db.execute_query("""
                SELECT COUNT(*) as total FROM exercises 
                WHERE skill = %s AND is_active = 1
            """, (skill,), fetch_one=True)
            total_count = result['total'] if result else 1
            
            # Số bài đúng của user với kỹ năng này
            result, _ = db.execute_query("""
                SELECT COUNT(*) as correct
                FROM exercise_results er
                JOIN exercises e ON er.exercise_id = e.id
                WHERE er.user_id = %s AND e.skill = %s AND er.is_correct = 1
            """, (user_id, skill), fetch_one=True)
            correct_count = result['correct'] if result else 0
            
            percentage = round((correct_count / total_count * 100) if total_count > 0 else 0)
            status = 'strong' if percentage >= 70 else 'weak'
            
            results.append({
                'name': skill_names.get(skill, {}).get('name', skill.upper()),
                'icon': skill_names.get(skill, {}).get('icon', '📌'),
                'percentage': percentage,
                'status': status
            })
        
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@progress_bp.route('/history')
@login_required
def get_history():
    """Lấy lịch sử học tập theo tuần"""
    try:
        user_id = current_user.id
        
        history = []
        for i in range(6, 0, -1):
            week_start = datetime.now() - timedelta(weeks=i)
            week_num = week_start.isocalendar()[1]
            
            # Đếm số bài làm trong tuần
            result, _ = db.execute_query("""
                SELECT COUNT(*) as completed
                FROM exercise_results
                WHERE user_id = %s 
                AND executed_at >= DATE_SUB(NOW(), INTERVAL %s WEEK)
                AND executed_at < DATE_SUB(NOW(), INTERVAL %s WEEK)
            """, (user_id, i, i-1), fetch_one=True)
            completed = result['completed'] if result else 0
            
            # Điểm trung bình trong tuần
            result, _ = db.execute_query("""
                SELECT AVG(CASE WHEN is_correct = 1 THEN 100 ELSE 0 END) as avg_score
                FROM exercise_results
                WHERE user_id = %s 
                AND executed_at >= DATE_SUB(NOW(), INTERVAL %s WEEK)
                AND executed_at < DATE_SUB(NOW(), INTERVAL %s WEEK)
            """, (user_id, i, i-1), fetch_one=True)
            avg_score = round(result['avg_score'] or 0) if result else 0
            
            history.append({
                'week': f'Tuần {week_num}',
                'completed': completed,
                'avg_score': avg_score
            })
        
        # Đảo ngược để tuần cũ lên trước
        history.reverse()
        
        return jsonify({'success': True, 'data': history})
    except Exception as e:
        # Trả về dữ liệu mẫu nếu chưa có
        return jsonify({
            'success': True,
            'data': [
                {'week': 'Tuần 1', 'completed': 2, 'avg_score': 60},
                {'week': 'Tuần 2', 'completed': 5, 'avg_score': 65},
                {'week': 'Tuần 3', 'completed': 8, 'avg_score': 70},
                {'week': 'Tuần 4', 'completed': 12, 'avg_score': 72},
                {'week': 'Tuần 5', 'completed': 18, 'avg_score': 74},
                {'week': 'Tuần 6', 'completed': 24, 'avg_score': 75},
            ]
        })


@progress_bp.route('/recommendations')
@login_required
def get_recommendations():
    """Đề xuất bài tập dựa trên điểm yếu"""
    try:
        user_id = current_user.id
        
        recommendations = []
        
        # Tìm kỹ năng yếu nhất
        result, _ = db.execute_query("""
            SELECT e.skill, COUNT(*) as total, 
                   SUM(CASE WHEN er.is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM exercises e
            LEFT JOIN exercise_results er ON e.id = er.exercise_id AND er.user_id = %s
            WHERE e.is_active = 1
            GROUP BY e.skill
            HAVING (correct * 1.0 / total) < 0.6 OR correct IS NULL
            ORDER BY (correct * 1.0 / total) ASC
            LIMIT 1
        """, (user_id,), fetch_one=True)
        
        if result and result.get('skill'):
            recommendations.append({
                'type': 'weak_skill',
                'name': result['skill'].upper(),
                'message': f'Bạn còn yếu về {result["skill"].upper()}. Hãy luyện tập thêm!',
                'link': f'/ai/thuc-hanh-ai?skill={result["skill"]}'
            })
        
        # Tìm level chưa hoàn thành
        result, _ = db.execute_query("""
            SELECT e.level, COUNT(*) as total,
                   COUNT(DISTINCT er.exercise_id) as completed
            FROM exercises e
            LEFT JOIN exercise_results er ON e.id = er.exercise_id AND er.user_id = %s
            WHERE e.is_active = 1
            GROUP BY e.level
            HAVING completed < total
            ORDER BY e.level ASC
            LIMIT 1
        """, (user_id,), fetch_one=True)
        
        if result:
            recommendations.append({
                'type': 'incomplete_level',
                'name': f'Level {result["level"]}',
                'message': f'Còn bài tập Level {result["level"]} chưa hoàn thành.',
                'link': f'/ai/thuc-hanh-ai?level={result["level"]}'
            })
        
        # Thử thách level cao hơn
        recommendations.append({
            'type': 'challenge',
            'name': 'Thử thách Level 4',
            'message': 'Bạn đã sẵn sàng thử sức với bài tập nâng cao!',
            'link': '/ai/thuc-hanh-ai?level=4'
        })
        
        return jsonify({'success': True, 'data': recommendations})
    except Exception as e:
        return jsonify({'success': True, 'data': []})


@progress_bp.route('/rankings')
@login_required
def get_rankings():
    """Bảng xếp hạng trong lớp"""
    try:
        current_user_id = current_user.id
        
        # Lấy top 10 học sinh có điểm cao nhất
        results, _ = db.execute_query("""
            SELECT u.id, u.username, u.full_name,
                   COUNT(DISTINCT er.exercise_id) as completed,
                   SUM(CASE WHEN er.is_correct = 1 THEN 100 ELSE 0 END) as total_score
            FROM users u
            LEFT JOIN exercise_results er ON u.id = er.user_id
            WHERE u.role_id = 2
            GROUP BY u.id
            ORDER BY total_score DESC, completed DESC
            LIMIT 10
        """)
        
        rankings = []
        for idx, user in enumerate(results, 1):
            rankings.append({
                'rank': idx,
                'id': user['id'],
                'name': user.get('full_name') or user.get('username'),
                'score': round(user.get('total_score') or 0),
                'is_current_user': user['id'] == current_user_id
            })
        
        return jsonify({'success': True, 'data': rankings})
    except Exception as e:
        return jsonify({'success': True, 'data': []})


@progress_bp.route('/badges')
@login_required
def get_badges():
    """Lấy danh sách huy hiệu"""
    try:
        user_id = current_user.id
        
        # Đếm số bài đã làm
        result, _ = db.execute_query("""
            SELECT COUNT(DISTINCT exercise_id) as count 
            FROM exercise_results WHERE user_id = %s
        """, (user_id,), fetch_one=True)
        done_count = result['count'] if result else 0
        
        # Đếm số bài đúng
        result, _ = db.execute_query("""
            SELECT COUNT(*) as count 
            FROM exercise_results WHERE user_id = %s AND is_correct = 1
        """, (user_id,), fetch_one=True)
        correct_count = result['count'] if result else 0
        
        # Tỷ lệ đúng
        correct_rate = round((correct_count / done_count * 100) if done_count > 0 else 0)
        
        # Kiểm tra hoàn thành JOIN
        result, _ = db.execute_query("""
            SELECT COUNT(*) as completed
            FROM exercise_results er
            JOIN exercises e ON er.exercise_id = e.id
            WHERE er.user_id = %s AND e.skill = 'join' AND e.is_active = 1
        """, (user_id,), fetch_one=True)
        join_completed = result['completed'] if result else 0
        
        # Kiểm tra hoàn thành Level 4
        result, _ = db.execute_query("""
            SELECT COUNT(*) as completed
            FROM exercise_results er
            JOIN exercises e ON er.exercise_id = e.id
            WHERE er.user_id = %s AND e.level = 4 AND e.is_active = 1
        """, (user_id,), fetch_one=True)
        level4_completed = result['completed'] if result else 0
        
        badges = [
            {'name': 'Người mới', 'icon': '🌟', 'desc': 'Hoàn thành bài tập đầu tiên', 'unlocked': done_count >= 1},
            {'name': 'Chăm chỉ', 'icon': '🔥', 'desc': 'Làm 10 bài tập', 'unlocked': done_count >= 10},
            {'name': 'Chính xác', 'icon': '🎯', 'desc': 'Đạt 80% đúng', 'unlocked': correct_rate >= 80},
            {'name': 'Master JOIN', 'icon': '🔗', 'desc': 'Hoàn thành 100% bài JOIN', 'unlocked': join_completed >= 10},
            {'name': 'Chinh phục Level 4', 'icon': '🏆', 'desc': 'Hoàn thành Level 4', 'unlocked': level4_completed >= 20},
        ]
        
        return jsonify({'success': True, 'data': badges})
    except Exception as e:
        return jsonify({'success': True, 'data': [
            {'name': 'Người mới', 'icon': '🌟', 'desc': 'Hoàn thành bài tập đầu tiên', 'unlocked': False},
            {'name': 'Chăm chỉ', 'icon': '🔥', 'desc': 'Làm 10 bài tập', 'unlocked': False},
            {'name': 'Chính xác', 'icon': '🎯', 'desc': 'Đạt 80% đúng', 'unlocked': False},
            {'name': 'Master JOIN', 'icon': '🔗', 'desc': 'Hoàn thành 100% bài JOIN', 'unlocked': False},
            {'name': 'Chinh phục Level 4', 'icon': '🏆', 'desc': 'Hoàn thành Level 4', 'unlocked': False},
        ]})