# application/controllers/composer_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from application.services.database_service import DatabaseService
from application.services.cache_service import CacheService
from application.utils.helpers import allowed_image, allowed_file
from application.extensions import csrf
import os
import time
from werkzeug.utils import secure_filename
from config import Config

composer_bp = Blueprint('composer', __name__)
db = DatabaseService()
cache = CacheService(timeout=Config.CACHE_TIMEOUT)


@composer_bp.route('/')
def list_composers():
    """Danh sách nhạc sĩ"""
    page = request.args.get('page', 1, type=int)
    per_page = Config.ITEMS_PER_PAGE
    search_query = request.args.get('search', '').strip()
    
    # Cache key
    cache_key = cache.generate_key('composer_list', page, per_page, search_query)
    cached_data = cache.cache.get(cache_key)
    
    if cached_data:
        return render_template('nhacsi/nhacsi_list.html', **cached_data)
    
    # Đếm tổng số
    if search_query:
        count_query = """
            SELECT COUNT(*) as total 
            FROM nhacsi 
            WHERE tennhacsi LIKE %s OR quequan LIKE %s OR tieusu LIKE %s
        """
        count_params = [f"%{search_query}%"] * 3
    else:
        count_query = "SELECT COUNT(*) as total FROM nhacsi"
        count_params = None
    
    count_result, _ = db.execute_query(count_query, count_params, fetch_one=True)
    total = count_result['total'] if count_result else 0
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Lấy dữ liệu
    offset = (page - 1) * per_page
    if search_query:
        query = """
            SELECT * FROM nhacsi 
            WHERE tennhacsi LIKE %s OR quequan LIKE %s OR tieusu LIKE %s
            ORDER BY tennhacsi 
            LIMIT %s OFFSET %s
        """
        params = [f"%{search_query}%"] * 3 + [per_page, offset]
    else:
        query = """
            SELECT * FROM nhacsi 
            ORDER BY tennhacsi 
            LIMIT %s OFFSET %s
        """
        params = [per_page, offset]
    
    composers, _ = db.execute_query(query, params)
    
    template_data = {
        'nhacsi_list': composers or [],
        'page': page,
        'total_pages': total_pages,
        'search_query': search_query,
        'per_page': per_page
    }
    
    # Cache kết quả
    cache.cache.set(cache_key, template_data)
    
    return render_template('nhacsi/nhacsi_list.html', **template_data)


@composer_bp.route('/<int:id>')
def composer_detail(id):
    """Chi tiết nhạc sĩ"""
    # Lấy thông tin nhạc sĩ
    query = """
        SELECT n.*, DATE_FORMAT(n.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM nhacsi n
        WHERE n.idnhacsi = %s
    """
    composer, _ = db.execute_query(query, (id,), fetch_one=True)
    
    if not composer:
        flash('Không tìm thấy nhạc sĩ', 'danger')
        return redirect(url_for('composer.list_composers'))
    
    # Lấy danh sách bản nhạc
    songs_query = """
        SELECT b.*, COUNT(bt.idbanthuam) as so_luong_banthuam,
               DATE_FORMAT(b.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM bannhac b
        LEFT JOIN banthuam bt ON b.idbannhac = bt.idbannhac
        WHERE b.idnhacsi = %s
        GROUP BY b.idbannhac
        ORDER BY b.created_at DESC
    """
    songs, _ = db.execute_query(songs_query, (id,))
    
    # Đếm tổng bản thu âm
    total_recordings, _ = db.execute_query("""
        SELECT COUNT(DISTINCT bt.idbanthuam) as total
        FROM banthuam bt
        JOIN bannhac b ON bt.idbannhac = b.idbannhac
        WHERE b.idnhacsi = %s
    """, (id,), fetch_one=True)
    
    # Đếm số ca sĩ
    artists_count, _ = db.execute_query("""
        SELECT COUNT(DISTINCT bt.idcasi) as count
        FROM banthuam bt
        JOIN bannhac b ON bt.idbannhac = b.idbannhac
        WHERE b.idnhacsi = %s
    """, (id,), fetch_one=True)
    
    return render_template('nhacsi/nhacsi_detail.html',
                         nhacsi=composer,
                         songs=songs or [],
                         total_recordings=total_recordings['total'] if total_recordings else 0,
                         artists_count=artists_count['count'] if artists_count else 0)


@composer_bp.route('/add', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def add_composer():
    """Thêm nhạc sĩ"""
    if not current_user.is_editor():
        flash('Bạn không có quyền thêm nhạc sĩ', 'danger')
        return redirect(url_for('composer.list_composers'))
    
    if request.method == 'GET':
        return render_template('nhacsi/nhacsi_add.html')
    
    tennhacsi = request.form.get('tennhacsi', '').strip()
    if not tennhacsi:
        flash('Tên nhạc sĩ không được để trống', 'danger')
        return redirect(url_for('composer.add_composer'))
    
    # Xử lý avatar
    avatar_path = None
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename:
            if not allowed_image(file.filename):
                flash('Định dạng ảnh không hợp lệ', 'danger')
                return redirect(url_for('composer.add_composer'))
            
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"ns_{int(time.time())}.{ext}")
            save_path = os.path.join(Config.ARTIST_IMAGE_FOLDER, filename)
            file.save(save_path)
            avatar_path = filename
    
    # Insert vào database
    query = """
        INSERT INTO nhacsi (tennhacsi, ngaysinh, gioitinh, quequan, tieusu, avatar)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (
        tennhacsi,
        request.form.get('ngaysinh'),
        request.form.get('gioitinh'),
        request.form.get('quequan'),
        request.form.get('tieusu'),
        avatar_path
    )
    
    _, error = db.execute_query(query, params)
    
    if error:
        flash(f'Lỗi: {error}', 'danger')
    else:
        # Invalidate cache
        cache.invalidate_pattern('composer_list')
        flash('Thêm nhạc sĩ thành công!', 'success')
        return redirect(url_for('composer.list_composers'))
    
    return redirect(url_for('composer.add_composer'))


@composer_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def edit_composer(id):
    """Chỉnh sửa nhạc sĩ"""
    if not current_user.is_editor():
        flash('Bạn không có quyền chỉnh sửa nhạc sĩ', 'danger')
        return redirect(url_for('composer.list_composers'))
    
    if request.method == 'GET':
        composer, _ = db.execute_query(
            "SELECT * FROM nhacsi WHERE idnhacsi = %s", (id,), fetch_one=True
        )
        
        if not composer:
            flash('Không tìm thấy nhạc sĩ', 'danger')
            return redirect(url_for('composer.list_composers'))
        
        return render_template('nhacsi/nhacsi_edit.html', nhacsi=composer)
    
    # POST - Update
    tennhacsi = request.form.get('tennhacsi', '').strip()
    if not tennhacsi:
        flash('Tên nhạc sĩ không được để trống', 'danger')
        return redirect(url_for('composer.edit_composer', id=id))
    
    query = """
        UPDATE nhacsi 
        SET tennhacsi = %s, ngaysinh = %s, gioitinh = %s, 
            quequan = %s, tieusu = %s
        WHERE idnhacsi = %s
    """
    params = (
        tennhacsi,
        request.form.get('ngaysinh'),
        request.form.get('gioitinh'),
        request.form.get('quequan'),
        request.form.get('tieusu'),
        id
    )
    
    _, error = db.execute_query(query, params)
    
    if error:
        flash(f'Lỗi: {error}', 'danger')
    else:
        # Invalidate cache
        cache.invalidate_pattern('composer_list')
        flash('Cập nhật nhạc sĩ thành công!', 'success')
    
    return redirect(url_for('composer.composer_detail', id=id))


@composer_bp.route('/api/<int:id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_composer(id):
    """Xóa nhạc sĩ (API)"""
    if not current_user.is_admin():
        return jsonify({"success": False, "message": "Không có quyền"}), 403
    
    # Kiểm tra tồn tại
    composer, _ = db.execute_query(
        "SELECT * FROM nhacsi WHERE idnhacsi = %s", (id,), fetch_one=True
    )
    
    if not composer:
        return jsonify({"success": False, "message": "Nhạc sĩ không tồn tại"}), 404
    
    # Kiểm tra bản nhạc liên quan
    count, _ = db.execute_query(
        "SELECT COUNT(*) as count FROM bannhac WHERE idnhacsi = %s", (id,), fetch_one=True
    )
    
    if count and count['count'] > 0:
        return jsonify({"success": False, "message": "Không thể xóa nhạc sĩ đã có sáng tác"}), 400
    
    # Xóa ảnh nếu có
    if composer.get('avatar'):
        file_path = os.path.join(Config.ARTIST_IMAGE_FOLDER, composer['avatar'])
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # Xóa nhạc sĩ
    _, error = db.execute_query("DELETE FROM nhacsi WHERE idnhacsi = %s", (id,))
    
    if error:
        return jsonify({"success": False, "message": str(error)}), 500
    
    # Invalidate cache
    cache.invalidate_pattern('composer_list')
    
    return jsonify({"success": True, "message": "Xóa nhạc sĩ thành công"})