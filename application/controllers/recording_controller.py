# application/controllers/recording_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import time
import logging

from application.services.database_service import DatabaseService
from application.utils.helpers import allowed_file
from config import Config

logger = logging.getLogger(__name__)
recording_bp = Blueprint('recording', __name__)
db = DatabaseService()


@recording_bp.route('/')
def list_recordings():
    """Danh sách bản thu âm"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    search_query = request.args.get('q', '').strip()
    artist_id = request.args.get('artist', '')
    sort_option = request.args.get('sort', 'newest')
    
    # Query cơ bản
    query = """
        SELECT ba.*, bn.tenbannhac, c.tencasi, ns.tennhacsi,
               DATE_FORMAT(ba.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM banthuam ba
        JOIN bannhac bn ON ba.idbannhac = bn.idbannhac
        JOIN casi c ON ba.idcasi = c.idcasi
        JOIN nhacsi ns ON bn.idnhacsi = ns.idnhacsi
        WHERE 1=1
    """
    params = []
    
    if search_query:
        query += " AND (bn.tenbannhac LIKE %s OR c.tencasi LIKE %s)"
        search_pattern = f"%{search_query}%"
        params.extend([search_pattern, search_pattern])
    
    if artist_id:
        query += " AND ba.idcasi = %s"
        params.append(artist_id)
    
    # Sắp xếp
    sort_map = {
        'newest': 'ba.created_at DESC',
        'oldest': 'ba.created_at ASC',
        'name_asc': 'bn.tenbannhac ASC',
        'name_desc': 'bn.tenbannhac DESC'
    }
    query += f" ORDER BY {sort_map.get(sort_option, 'ba.created_at DESC')}"
    
    # Đếm tổng số
    count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
    count_params = params.copy()
    count_result, _ = db.execute_query(count_query, count_params if count_params else None, fetch_one=True)
    total = count_result['total'] if count_result else 0
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Lấy dữ liệu phân trang
    offset = (page - 1) * per_page
    paginated_query = query + " LIMIT %s OFFSET %s"
    paginated_params = params + [per_page, offset]
    
    recordings, _ = db.execute_query(paginated_query, paginated_params)
    
    # Lấy danh sách ca sĩ cho filter
    artists, _ = db.execute_query("SELECT idcasi, tencasi FROM casi ORDER BY tencasi")
    
    return render_template('banthuam/banthuam_list.html',
                         banthuam_list=recordings or [],
                         artists=artists or [],
                         page=page,
                         per_page=per_page,
                         total_pages=total_pages,
                         search_query=search_query,
                         artist_id=artist_id,
                         sort_option=sort_option)


@recording_bp.route('/detail/<int:id>')
def recording_detail(id):
    """Chi tiết bản thu âm"""
    query = """
        SELECT ba.*, bn.tenbannhac, c.tencasi, ns.tennhacsi,
               DATE_FORMAT(ba.ngaythuam, '%%d/%%m/%%Y') as ngaythu,
               DATE_FORMAT(ba.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM banthuam ba
        JOIN bannhac bn ON ba.idbannhac = bn.idbannhac
        JOIN casi c ON ba.idcasi = c.idcasi
        JOIN nhacsi ns ON bn.idnhacsi = ns.idnhacsi
        WHERE ba.idbanthuam = %s
    """
    recording, _ = db.execute_query(query, (id,), fetch_one=True)
    
    if not recording:
        flash('Không tìm thấy bản thu âm', 'danger')
        return redirect(url_for('recording.list_recordings'))
    
    # Lấy bản thu liên quan
    related, _ = db.execute_query("""
        SELECT ba.idbanthuam, c.tencasi, 
               DATE_FORMAT(ba.ngaythuam, '%%d/%%m/%%Y') as ngaythu,
               ba.thoiluong
        FROM banthuam ba
        JOIN casi c ON ba.idcasi = c.idcasi
        WHERE ba.idbannhac = %s AND ba.idbanthuam != %s
        ORDER BY ba.created_at DESC
        LIMIT 5
    """, (recording['idbannhac'], id))
    
    return render_template('banthuam/banthuam_detail.html',
                         recording=recording,
                         related_recordings=related or [])


@recording_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_recording():
    """Thêm bản thu âm"""
    if not current_user.is_editor():
        flash('Bạn không có quyền thêm bản thu âm', 'danger')
        return redirect(url_for('recording.list_recordings'))
    
    if request.method == 'GET':
        songs, _ = db.execute_query("""
            SELECT b.idbannhac, b.tenbannhac, n.tennhacsi 
            FROM bannhac b
            JOIN nhacsi n ON b.idnhacsi = n.idnhacsi
            ORDER BY b.tenbannhac
        """)
        artists, _ = db.execute_query("SELECT idcasi, tencasi FROM casi ORDER BY tencasi")
        return render_template('banthuam/banthuam_add.html', 
                             songs=songs or [],
                             artists=artists or [])
    
    idbannhac = request.form.get('idbannhac')
    idcasi = request.form.get('idcasi')
    
    if not idbannhac or not idcasi:
        flash('Vui lòng chọn bài hát và ca sĩ', 'danger')
        return redirect(url_for('recording.add_recording'))
    
    # Xử lý file upload
    file_path = None
    if 'audio_file' in request.files:
        file = request.files['audio_file']
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Định dạng file không hợp lệ', 'danger')
                return redirect(url_for('recording.add_recording'))
            
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"recording_{int(time.time())}.{ext}")
            save_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(save_path)
            file_path = filename
    
    if not file_path:
        flash('Vui lòng chọn file âm thanh', 'danger')
        return redirect(url_for('recording.add_recording'))
    
    query = """
        INSERT INTO banthuam (idbannhac, idcasi, ngaythuam, thoiluong, lyrics, ghichu, file_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        idbannhac,
        idcasi,
        request.form.get('ngaythuam'),
        request.form.get('thoiluong'),
        request.form.get('lyrics', ''),
        request.form.get('ghichu', ''),
        file_path
    )
    
    _, error = db.execute_query(query, params)
    if error:
        flash(f'Lỗi: {error}', 'danger')
    else:
        flash('Thêm bản thu âm thành công!', 'success')
        return redirect(url_for('recording.list_recordings'))
    
    return redirect(url_for('recording.add_recording'))


@recording_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_recording(id):
    """Chỉnh sửa bản thu âm"""
    if not current_user.is_editor():
        flash('Bạn không có quyền chỉnh sửa', 'danger')
        return redirect(url_for('recording.list_recordings'))
    
    if request.method == 'GET':
        recording, _ = db.execute_query("""
            SELECT * FROM banthuam WHERE idbanthuam = %s
        """, (id,), fetch_one=True)
        if not recording:
            flash('Không tìm thấy bản thu âm', 'danger')
            return redirect(url_for('recording.list_recordings'))
        
        songs, _ = db.execute_query("""
            SELECT b.idbannhac, b.tenbannhac, n.tennhacsi 
            FROM bannhac b
            JOIN nhacsi n ON b.idnhacsi = n.idnhacsi
            ORDER BY b.tenbannhac
        """)
        artists, _ = db.execute_query("SELECT idcasi, tencasi FROM casi ORDER BY tencasi")
        
        return render_template('banthuam/banthuam_edit.html',
                             banthuam=recording,
                             songs=songs or [],
                             artists=artists or [])
    
    idbannhac = request.form.get('idbannhac')
    idcasi = request.form.get('idcasi')
    
    if not idbannhac or not idcasi:
        flash('Vui lòng chọn bài hát và ca sĩ', 'danger')
        return redirect(url_for('recording.edit_recording', id=id))
    
    query = """
        UPDATE banthuam 
        SET idbannhac = %s, idcasi = %s, ngaythuam = %s, 
            thoiluong = %s, lyrics = %s, ghichu = %s
        WHERE idbanthuam = %s
    """
    params = (
        idbannhac,
        idcasi,
        request.form.get('ngaythuam'),
        request.form.get('thoiluong'),
        request.form.get('lyrics', ''),
        request.form.get('ghichu', ''),
        id
    )
    
    _, error = db.execute_query(query, params)
    if error:
        flash(f'Lỗi: {error}', 'danger')
    else:
        flash('Cập nhật bản thu âm thành công!', 'success')
    
    return redirect(url_for('recording.recording_detail', id=id))


@recording_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_recording(id):
    """Xóa bản thu âm"""
    if not current_user.is_admin():
        flash('Bạn không có quyền xóa', 'danger')
        return redirect(url_for('recording.list_recordings'))
    
    recording, _ = db.execute_query(
        "SELECT file_path FROM banthuam WHERE idbanthuam = %s", (id,), fetch_one=True
    )
    
    if recording and recording.get('file_path'):
        file_path = os.path.join(Config.UPLOAD_FOLDER, recording['file_path'])
        if os.path.exists(file_path):
            os.remove(file_path)
    
    _, error = db.execute_query("DELETE FROM banthuam WHERE idbanthuam = %s", (id,))
    if error:
        flash(f'Lỗi khi xóa: {error}', 'danger')
    else:
        flash('Xóa bản thu âm thành công!', 'success')
    
    return redirect(url_for('recording.list_recordings'))


@recording_bp.route('/api/<int:id>', methods=['DELETE'])
@login_required
def delete_recording_api(id):
    """Xóa bản thu âm (API)"""
    if not current_user.is_admin():
        return jsonify({"success": False, "message": "Không có quyền"}), 403
    
    recording, _ = db.execute_query(
        "SELECT file_path FROM banthuam WHERE idbanthuam = %s", (id,), fetch_one=True
    )
    
    if not recording:
        return jsonify({"success": False, "message": "Bản thu âm không tồn tại"}), 404
    
    if recording.get('file_path'):
        file_path = os.path.join(Config.UPLOAD_FOLDER, recording['file_path'])
        if os.path.exists(file_path):
            os.remove(file_path)
    
    _, error = db.execute_query("DELETE FROM banthuam WHERE idbanthuam = %s", (id,))
    if error:
        return jsonify({"success": False, "message": str(error)}), 500
    
    return jsonify({"success": True, "message": "Xóa bản thu âm thành công"})