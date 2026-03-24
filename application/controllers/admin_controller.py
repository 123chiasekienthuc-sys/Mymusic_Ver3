# application/controllers/admin_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from application.services.database_service import DatabaseService

admin_bp = Blueprint('admin', __name__)
db = DatabaseService()


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Trang tổng quan quản trị"""
    if not current_user.is_admin():
        flash('Bạn không có quyền truy cập trang này', 'danger')
        return redirect(url_for('main.index'))
    
    stats = {}
    tables = ['nhacsi', 'casi', 'bannhac', 'banthuam', 'users']
    for table in tables:
        result, _ = db.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch_one=True)
        stats[table] = result['count'] if result else 0
    
    exercise_stats = {}
    result, _ = db.execute_query("SELECT COUNT(*) as count FROM exercises", fetch_one=True)
    exercise_stats['total'] = result['count'] if result else 0
    
    result, _ = db.execute_query("SELECT COUNT(*) as count FROM exercise_results", fetch_one=True)
    exercise_stats['attempts'] = result['count'] if result else 0
    
    return render_template('admin/dashboard.html', stats=stats, exercise_stats=exercise_stats)


@admin_bp.route('/users')
@login_required
def admin_users():
    """Quản lý người dùng"""
    if not current_user.is_admin():
        flash('Bạn không có quyền truy cập trang này', 'danger')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    query = """
        SELECT u.*, r.name as role_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        ORDER BY u.created_at DESC
        LIMIT %s OFFSET %s
    """
    users, error = db.execute_query(query, (per_page, offset))
    
    count_query = "SELECT COUNT(*) as total FROM users"
    count_result, _ = db.execute_query(count_query, fetch_one=True)
    total = count_result['total'] if count_result else 0
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('admin/users.html', users=users or [], page=page, total_pages=total_pages)

@admin_bp.route('/exercises')
@login_required
def admin_exercises():
    """Trang quản lý bài tập (admin)"""
    if not current_user.is_admin() and not current_user.is_editor():
        flash('Bạn không có quyền truy cập trang này', 'danger')
        return redirect(url_for('main.index'))
    
    return render_template('admin/exercises.html')


@admin_bp.route('/exercise-results')
@login_required
def admin_exercise_results():
    """Xem kết quả thực hành của học sinh"""
    if not current_user.is_admin() and not current_user.is_editor():
        flash('Bạn không có quyền truy cập trang này', 'danger')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    query = """
        SELECT er.*, e.code, e.title, e.level 
        FROM exercise_results er
        JOIN exercises e ON er.exercise_id = e.id
        ORDER BY er.executed_at DESC
        LIMIT %s OFFSET %s
    """
    results, error = db.execute_query(query, (per_page, offset))
    
    count_query = "SELECT COUNT(*) as total FROM exercise_results"
    count_result, _ = db.execute_query(count_query, fetch_one=True)
    total = count_result['total'] if count_result else 0
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('admin/results.html', 
                         results=results or [],
                         page=page,
                         total_pages=total_pages)


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
def change_role(user_id):
    """Thay đổi vai trò người dùng"""
    if not current_user.is_admin():
        return jsonify({"success": False, "message": "Không có quyền"}), 403
    
    data = request.get_json()
    new_role_id = data.get('role_id')
    
    if new_role_id not in [1, 2, 3]:
        return jsonify({"success": False, "message": "Vai trò không hợp lệ"}), 400
    
    query = "UPDATE users SET role_id = %s WHERE id = %s"
    _, error = db.execute_query(query, (new_role_id, user_id))
    
    if error:
        return jsonify({"success": False, "message": str(error)}), 500
    
    return jsonify({"success": True, "message": "Đã cập nhật vai trò"})


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_user(user_id):
    """Kích hoạt/vô hiệu hóa tài khoản"""
    if not current_user.is_admin():
        return jsonify({"success": False, "message": "Không có quyền"}), 403
    
    data = request.get_json()
    is_active = data.get('is_active')
    
    query = "UPDATE users SET is_active = %s WHERE id = %s"
    _, error = db.execute_query(query, (is_active, user_id))
    
    if error:
        return jsonify({"success": False, "message": str(error)}), 500
    
    status = "kích hoạt" if is_active else "vô hiệu hóa"
    return jsonify({"success": True, "message": f"Đã {status} tài khoản"})


@admin_bp.route('/activity')
@login_required
def admin_activity():
    """Xem hoạt động người dùng"""
    if not current_user.is_admin():
        flash('Bạn không có quyền truy cập trang này', 'danger')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    query = """
        SELECT a.*, u.username, u.full_name
        FROM user_activity a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
        LIMIT %s OFFSET %s
    """
    activities, error = db.execute_query(query, (per_page, offset))
    
    count_query = "SELECT COUNT(*) as total FROM user_activity"
    count_result, _ = db.execute_query(count_query, fetch_one=True)
    total = count_result['total'] if count_result else 0
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('admin/activity.html', activities=activities or [], page=page, total_pages=total_pages)