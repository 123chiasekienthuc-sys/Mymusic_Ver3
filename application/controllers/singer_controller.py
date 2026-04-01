# application/controllers/singer_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import time
import logging

from application.services.database_service import DatabaseService
from application.utils.helpers import allowed_image
from config import Config

logger = logging.getLogger(__name__)
singer_bp = Blueprint('singer', __name__)
db = DatabaseService()


@singer_bp.route('/')
def list_singers():
    """Danh sách ca sĩ"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    search_query = request.args.get('search', '').strip()
    
    # Đếm tổng số
    if search_query:
        count_query = "SELECT COUNT(*) as total FROM casi WHERE tencasi LIKE %s"
        count_params = [f"%{search_query}%"]
    else:
        count_query = "SELECT COUNT(*) as total FROM casi"
        count_params = None
    
    count_result, _ = db.execute_query(count_query, count_params, fetch_one=True)
    total = count_result['total'] if count_result else 0
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Lấy dữ liệu
    offset = (page - 1) * per_page
    if search_query:
        query = """
            SELECT c.*, COUNT(bt.idbanthuam) as soluong_banthuam,
                   DATE_FORMAT(c.created_at, '%%d/%%m/%%Y') as ngay_them
            FROM casi c
            LEFT JOIN banthuam bt ON c.idcasi = bt.idcasi
            WHERE c.tencasi LIKE %s
            GROUP BY c.idcasi
            ORDER BY c.tencasi
            LIMIT %s OFFSET %s
        """
        params = [f"%{search_query}%", per_page, offset]
    else:
        query = """
            SELECT c.*, COUNT(bt.idbanthuam) as soluong_banthuam,
                   DATE_FORMAT(c.created_at, '%%d/%%m/%%Y') as ngay_them
            FROM casi c
            LEFT JOIN banthuam bt ON c.idcasi = bt.idcasi
            GROUP BY c.idcasi
            ORDER BY c.tencasi
            LIMIT %s OFFSET %s
        """
        params = [per_page, offset]
    
    singers, _ = db.execute_query(query, params)
    
    return render_template('casi/casi_list.html',
                         casi_list=singers or [],
                         page=page,
                         total_pages=total_pages,
                         search_query=search_query,
                         per_page=per_page)


@singer_bp.route('/<int:id>')
def singer_detail(id):
    """Chi tiết ca sĩ"""
    query = """
        SELECT c.*, DATE_FORMAT(c.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM casi c WHERE c.idcasi = %s
    """
    singer, _ = db.execute_query(query, (id,), fetch_one=True)
    
    if not singer:
        flash('Không tìm thấy ca sĩ', 'danger')
        return redirect(url_for('singer.list_singers'))
    
    # Lấy danh sách bản thu âm
    recordings, _ = db.execute_query("""
        SELECT bt.*, bn.tenbannhac, ns.tennhacsi,
               DATE_FORMAT(bt.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM banthuam bt
        JOIN bannhac bn ON bt.idbannhac = bn.idbannhac
        JOIN nhacsi ns ON bn.idnhacsi = ns.idnhacsi
        WHERE bt.idcasi = %s
        ORDER BY bt.created_at DESC
    """, (id,))
    
    return render_template('casi/casi_detail.html',
                         casi=singer,
                         banthuam=recordings or [])


@singer_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_singer():
    """Thêm ca sĩ"""
    if not current_user.is_editor():
        flash('Bạn không có quyền thêm ca sĩ', 'danger')
        return redirect(url_for('singer.list_singers'))
    
    if request.method == 'GET':
        return render_template('casi/casi_add.html')
    
    tencasi = request.form.get('tencasi', '').strip()
    if not tencasi:
        flash('Tên ca sĩ không được để trống', 'danger')
        return redirect(url_for('singer.add_singer'))
    
    # Xử lý ảnh
    anhdaidien = None
    if 'anhdaidien' in request.files:
        file = request.files['anhdaidien']
        if file and file.filename:
            if not allowed_image(file.filename):
                flash('Định dạng ảnh không hợp lệ', 'danger')
                return redirect(url_for('singer.add_singer'))
            
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"cs_{int(time.time())}.{ext}")
            save_path = os.path.join(Config.SINGER_IMAGE_FOLDER, filename)
            file.save(save_path)
            anhdaidien = filename
    
    query = """
        INSERT INTO casi (tencasi, Ngaysinh, Sunghiep, anhdaidien)
        VALUES (%s, %s, %s, %s)
    """
    params = (
        tencasi,
        request.form.get('ngaysinh'),
        request.form.get('sunghiep'),
        anhdaidien
    )
    
    _, error = db.execute_query(query, params)
    if error:
        flash(f'Lỗi: {error}', 'danger')
    else:
        flash('Thêm ca sĩ thành công!', 'success')
        return redirect(url_for('singer.list_singers'))
    
    return redirect(url_for('singer.add_singer'))


@singer_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_singer(id):
    """Chỉnh sửa ca sĩ"""
    if not current_user.is_editor():
        flash('Bạn không có quyền chỉnh sửa', 'danger')
        return redirect(url_for('singer.list_singers'))
    
    if request.method == 'GET':
        singer, _ = db.execute_query(
            "SELECT * FROM casi WHERE idcasi = %s", (id,), fetch_one=True
        )
        if not singer:
            flash('Không tìm thấy ca sĩ', 'danger')
            return redirect(url_for('singer.list_singers'))
        return render_template('casi/casi_edit.html', casi=singer)
    
    tencasi = request.form.get('tencasi', '').strip()
    if not tencasi:
        flash('Tên ca sĩ không được để trống', 'danger')
        return redirect(url_for('singer.edit_singer', id=id))
    
    query = """
        UPDATE casi SET tencasi = %s, Ngaysinh = %s, Sunghiep = %s
        WHERE idcasi = %s
    """
    params = (
        tencasi,
        request.form.get('ngaysinh'),
        request.form.get('sunghiep'),
        id
    )
    
    _, error = db.execute_query(query, params)
    if error:
        flash(f'Lỗi: {error}', 'danger')
    else:
        flash('Cập nhật ca sĩ thành công!', 'success')
    
    return redirect(url_for('singer.singer_detail', id=id))


@singer_bp.route('/api/<int:id>', methods=['DELETE'])
@login_required
def delete_singer(id):
    """Xóa ca sĩ"""
    if not current_user.is_admin():
        return jsonify({"success": False, "message": "Không có quyền"}), 403
    
    singer, _ = db.execute_query(
        "SELECT * FROM casi WHERE idcasi = %s", (id,), fetch_one=True
    )
    if not singer:
        return jsonify({"success": False, "message": "Ca sĩ không tồn tại"}), 404
    
    # Kiểm tra bản thu âm
    count, _ = db.execute_query(
        "SELECT COUNT(*) as count FROM banthuam WHERE idcasi = %s", (id,), fetch_one=True
    )
    if count and count['count'] > 0:
        return jsonify({"success": False, "message": "Không thể xóa ca sĩ đã có bản thu âm"}), 400
    
    # Xóa ảnh
    if singer.get('anhdaidien'):
        file_path = os.path.join(Config.SINGER_IMAGE_FOLDER, singer['anhdaidien'])
        if os.path.exists(file_path):
            os.remove(file_path)
    
    _, error = db.execute_query("DELETE FROM casi WHERE idcasi = %s", (id,))
    if error:
        return jsonify({"success": False, "message": str(error)}), 500
    
    return jsonify({"success": True, "message": "Xóa ca sĩ thành công"})