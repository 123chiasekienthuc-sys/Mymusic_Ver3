# application/controllers/song_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging

from application.services.database_service import DatabaseService
from config import Config

logger = logging.getLogger(__name__)
song_bp = Blueprint('song', __name__)
db = DatabaseService()


@song_bp.route('/')
def list_songs():
    """Danh sách bản nhạc"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    nhacsi_id = request.args.get('nhacsi')
    sort_by = request.args.get('sort', 'newest')
    search = request.args.get('search', '').strip()
    
    # Xây dựng query
    query = """
        SELECT b.*, n.tennhacsi, COUNT(bt.idbanthuam) as soluong_banthuam,
               DATE_FORMAT(b.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM bannhac b
        JOIN nhacsi n ON b.idnhacsi = n.idnhacsi
        LEFT JOIN banthuam bt ON b.idbannhac = bt.idbannhac
        WHERE 1=1
    """
    params = []
    
    if nhacsi_id:
        query += " AND b.idnhacsi = %s"
        params.append(nhacsi_id)
    
    if search:
        query += " AND b.tenbannhac LIKE %s"
        params.append(f"%{search}%")
    
    query += " GROUP BY b.idbannhac"
    
    # Sắp xếp
    sort_map = {
        'newest': 'b.created_at DESC',
        'oldest': 'b.created_at ASC',
        'name_asc': 'b.tenbannhac ASC',
        'name_desc': 'b.tenbannhac DESC',
        'popular': 'soluong_banthuam DESC'
    }
    query += f" ORDER BY {sort_map.get(sort_by, 'b.created_at DESC')}"
    
    # Đếm tổng số
    count_query = "SELECT COUNT(*) as total FROM bannhac b WHERE 1=1"
    count_params = []
    if nhacsi_id:
        count_query += " AND b.idnhacsi = %s"
        count_params.append(nhacsi_id)
    if search:
        count_query += " AND b.tenbannhac LIKE %s"
        count_params.append(f"%{search}%")
    
    count_result, _ = db.execute_query(count_query, count_params if count_params else None, fetch_one=True)
    total = count_result['total'] if count_result else 0
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Lấy dữ liệu phân trang
    offset = (page - 1) * per_page
    paginated_query = query + f" LIMIT %s OFFSET %s"
    paginated_params = params + [per_page, offset]
    
    songs, _ = db.execute_query(paginated_query, paginated_params)
    
    # Lấy danh sách nhạc sĩ cho filter
    composers, _ = db.execute_query("SELECT idnhacsi, tennhacsi FROM nhacsi ORDER BY tennhacsi")
    
    return render_template('bannhac/bannhac_list.html',
                         bannhac_list=songs or [],
                         nhacsi_list=composers or [],
                         page=page,
                         total_pages=total_pages,
                         per_page=per_page,
                         nhacsi_id=nhacsi_id,
                         sort_by=sort_by,
                         search_query=search)


@song_bp.route('/<int:id>')
def song_detail(id):
    """Chi tiết bản nhạc"""
    query = """
        SELECT b.*, n.tennhacsi,
               DATE_FORMAT(b.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM bannhac b
        LEFT JOIN nhacsi n ON b.idnhacsi = n.idnhacsi
        WHERE b.idbannhac = %s
    """
    song, _ = db.execute_query(query, (id,), fetch_one=True)
    
    if not song:
        flash('Không tìm thấy bản nhạc', 'danger')
        return redirect(url_for('song.list_songs'))
    
    # Lấy danh sách bản thu âm
    recordings, _ = db.execute_query("""
        SELECT ba.*, c.tencasi,
               DATE_FORMAT(ba.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM banthuam ba
        LEFT JOIN casi c ON ba.idcasi = c.idcasi
        WHERE ba.idbannhac = %s
        ORDER BY ba.created_at DESC
    """, (id,))
    
    return render_template('bannhac/bannhac_detail.html',
                         bannhac=song,
                         banthuam=recordings or [])


@song_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_song():
    """Thêm bản nhạc"""
    if not current_user.is_editor():
        flash('Bạn không có quyền thêm bản nhạc', 'danger')
        return redirect(url_for('song.list_songs'))
    
    if request.method == 'GET':
        composers, _ = db.execute_query("SELECT idnhacsi, tennhacsi FROM nhacsi ORDER BY tennhacsi")
        return render_template('bannhac/bannhac_add.html', nhacsi_list=composers or [])
    
    tenbannhac = request.form.get('tenbannhac', '').strip()
    if not tenbannhac:
        flash('Tên bản nhạc không được để trống', 'danger')
        return redirect(url_for('song.add_song'))
    
    idnhacsi = request.form.get('idnhacsi')
    if not idnhacsi:
        flash('Vui lòng chọn nhạc sĩ', 'danger')
        return redirect(url_for('song.add_song'))
    
    query = """
        INSERT INTO bannhac (tenbannhac, theloai, idnhacsi)
        VALUES (%s, %s, %s)
    """
    params = (
        tenbannhac,
        request.form.get('theloai', ''),
        idnhacsi
    )
    
    _, error = db.execute_query(query, params)
    if error:
        flash(f'Lỗi: {error}', 'danger')
    else:
        flash('Thêm bản nhạc thành công!', 'success')
        return redirect(url_for('song.list_songs'))
    
    return redirect(url_for('song.add_song'))


@song_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_song(id):
    """Chỉnh sửa bản nhạc"""
    if not current_user.is_editor():
        flash('Bạn không có quyền chỉnh sửa', 'danger')
        return redirect(url_for('song.list_songs'))
    
    if request.method == 'GET':
        song, _ = db.execute_query(
            "SELECT * FROM bannhac WHERE idbannhac = %s", (id,), fetch_one=True
        )
        if not song:
            flash('Không tìm thấy bản nhạc', 'danger')
            return redirect(url_for('song.list_songs'))
        
        composers, _ = db.execute_query("SELECT idnhacsi, tennhacsi FROM nhacsi ORDER BY tennhacsi")
        return render_template('bannhac/bannhac_edit.html', 
                             bannhac=song, 
                             nhacsi_list=composers or [])
    
    tenbannhac = request.form.get('tenbannhac', '').strip()
    if not tenbannhac:
        flash('Tên bản nhạc không được để trống', 'danger')
        return redirect(url_for('song.edit_song', id=id))
    
    idnhacsi = request.form.get('idnhacsi')
    if not idnhacsi:
        flash('Vui lòng chọn nhạc sĩ', 'danger')
        return redirect(url_for('song.edit_song', id=id))
    
    query = """
        UPDATE bannhac SET tenbannhac = %s, theloai = %s, idnhacsi = %s
        WHERE idbannhac = %s
    """
    params = (
        tenbannhac,
        request.form.get('theloai', ''),
        idnhacsi,
        id
    )
    
    _, error = db.execute_query(query, params)
    if error:
        flash(f'Lỗi: {error}', 'danger')
    else:
        flash('Cập nhật bản nhạc thành công!', 'success')
    
    return redirect(url_for('song.song_detail', id=id))


@song_bp.route('/api/<int:id>', methods=['DELETE'])
@login_required
def delete_song(id):
    """Xóa bản nhạc"""
    if not current_user.is_admin():
        return jsonify({"success": False, "message": "Không có quyền"}), 403
    
    song, _ = db.execute_query(
        "SELECT * FROM bannhac WHERE idbannhac = %s", (id,), fetch_one=True
    )
    if not song:
        return jsonify({"success": False, "message": "Bản nhạc không tồn tại"}), 404
    
    # Kiểm tra bản thu âm
    count, _ = db.execute_query(
        "SELECT COUNT(*) as count FROM banthuam WHERE idbannhac = %s", (id,), fetch_one=True
    )
    if count and count['count'] > 0:
        return jsonify({"success": False, "message": "Không thể xóa bản nhạc đã có bản thu âm"}), 400
    
    _, error = db.execute_query("DELETE FROM bannhac WHERE idbannhac = %s", (id,))
    if error:
        return jsonify({"success": False, "message": str(error)}), 500
    
    return jsonify({"success": True, "message": "Xóa bản nhạc thành công"})