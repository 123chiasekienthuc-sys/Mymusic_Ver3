# application/controllers/main_controller.py
from flask import Blueprint, render_template, jsonify, request
from application.services.database_service import DatabaseService
from config import Config

main_bp = Blueprint('main', __name__)
db = DatabaseService()


@main_bp.route('/')
def index():
    """Trang chủ"""
    try:
        # Lấy thống kê
        stats = {}
        tables = ['nhacsi', 'casi', 'bannhac', 'banthuam']
        for table in tables:
            result, _ = db.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch_one=True)
            stats[table] = result['count'] if result else 0
        
        # Lấy bản nhạc nổi bật
        featured_songs, _ = db.execute_query("""
            SELECT b.idbannhac, b.tenbannhac, n.tennhacsi, 
                   COUNT(bt.idbanthuam) as so_luong_banthuam
            FROM bannhac b
            JOIN nhacsi n ON b.idnhacsi = n.idnhacsi
            LEFT JOIN banthuam bt ON b.idbannhac = bt.idbannhac
            GROUP BY b.idbannhac
            ORDER BY so_luong_banthuam DESC
            LIMIT 6
        """)
        
        # Lấy nhạc sĩ tiêu biểu
        composers, _ = db.execute_query("""
            SELECT n.idnhacsi, n.tennhacsi, n.avatar,
                   COUNT(b.idbannhac) as so_luong_bai_hat
            FROM nhacsi n
            LEFT JOIN bannhac b ON n.idnhacsi = b.idnhacsi
            GROUP BY n.idnhacsi
            ORDER BY so_luong_bai_hat DESC
            LIMIT 4
        """)
        
        # Lấy ca sĩ nổi bật
        singers, _ = db.execute_query("""
            SELECT c.idcasi, c.tencasi, c.anhdaidien,
                   COUNT(bt.idbanthuam) as so_luong_banthuam
            FROM casi c
            LEFT JOIN banthuam bt ON c.idcasi = bt.idcasi
            GROUP BY c.idcasi
            ORDER BY so_luong_banthuam DESC
            LIMIT 4
        """)
        
        # Lấy bản thu âm mới nhất
        latest_recordings, _ = db.execute_query("""
            SELECT bt.idbanthuam, bn.tenbannhac, c.tencasi, 
                   DATE_FORMAT(bt.created_at, '%%d/%%m/%%Y') as created_at
            FROM banthuam bt
            JOIN bannhac bn ON bt.idbannhac = bn.idbannhac
            JOIN casi c ON bt.idcasi = c.idcasi
            ORDER BY bt.created_at DESC
            LIMIT 6
        """)
        
        return render_template('index.html',
                             stats=stats,
                             featured_songs=featured_songs or [],
                             composers=composers or [],
                             singers=singers or [],
                             latest_recordings=latest_recordings or [])
                             
    except Exception as e:
        return render_template('index.html',
                             stats={'nhacsi':0, 'casi':0, 'bannhac':0, 'banthuam':0},
                             featured_songs=[],
                             composers=[],
                             singers=[],
                             latest_recordings=[])


@main_bp.route('/library')
def library():
    """Thư viện"""
    return render_template('library.html')


@main_bp.route('/trending')
def trending():
    """Thịnh hành"""
    return render_template('trending.html')


@main_bp.route('/search')
def search():
    """Tìm kiếm"""
    query = request.args.get('q', '').strip()
    if not query:
        return render_template('search.html', query=query, results={})
    
    results = {'nhacsi': [], 'casi': [], 'bannhac': [], 'banthuam': []}
    
    # Tìm nhạc sĩ
    composers, _ = db.execute_query(
        "SELECT * FROM nhacsi WHERE tennhacsi LIKE %s LIMIT 10",
        (f'%{query}%',)
    )
    if composers:
        results['nhacsi'] = composers
    
    # Tìm ca sĩ
    singers, _ = db.execute_query(
        "SELECT * FROM casi WHERE tencasi LIKE %s LIMIT 10",
        (f'%{query}%',)
    )
    if singers:
        results['casi'] = singers
    
    # Tìm bản nhạc
    songs, _ = db.execute_query("""
        SELECT b.*, n.tennhacsi FROM bannhac b
        JOIN nhacsi n ON b.idnhacsi = n.idnhacsi
        WHERE b.tenbannhac LIKE %s LIMIT 10
    """, (f'%{query}%',))
    if songs:
        results['bannhac'] = songs
    
    # Tìm bản thu âm
    recordings, _ = db.execute_query("""
        SELECT bt.*, bn.tenbannhac, c.tencasi FROM banthuam bt
        JOIN bannhac bn ON bt.idbannhac = bn.idbannhac
        JOIN casi c ON bt.idcasi = c.idcasi
        WHERE bn.tenbannhac LIKE %s OR c.tencasi LIKE %s LIMIT 10
    """, (f'%{query}%', f'%{query}%'))
    if recordings:
        results['banthuam'] = recordings
    
    return render_template('search.html', query=query, results=results)


# API Routes
@main_bp.route('/api/stats')
def get_stats():
    """API thống kê"""
    queries = {
        'nhacsi': "SELECT COUNT(*) as count FROM nhacsi",
        'casi': "SELECT COUNT(*) as count FROM casi",
        'bannhac': "SELECT COUNT(*) as count FROM bannhac",
        'banthuam': "SELECT COUNT(*) as count FROM banthuam"
    }
    
    stats = {}
    for key, query in queries.items():
        result, error = db.execute_query(query, fetch_one=True)
        if error:
            return jsonify({'error': error}), 500
        stats[key] = result['count'] if result else 0
    
    return jsonify(stats)


@main_bp.route('/api/nhacsi')
def api_nhacsi():
    """API danh sách nhạc sĩ"""
    result, error = db.execute_query("SELECT * FROM nhacsi ORDER BY tennhacsi")
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result or [])


@main_bp.route('/api/casi')
def api_casi():
    """API danh sách ca sĩ"""
    result, error = db.execute_query("SELECT * FROM casi ORDER BY tencasi")
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result or [])


@main_bp.route('/api/nhacsi/latest')
def api_nhacsi_latest():
    """API lấy nhạc sĩ mới nhất"""
    result, error = db.execute_query("""
        SELECT idnhacsi, tennhacsi, tieusu,
               DATE_FORMAT(created_at, '%%d/%%m/%%Y') as ngay_them
        FROM nhacsi
        ORDER BY created_at DESC
        LIMIT 5
    """)
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result or [])


@main_bp.route('/api/casi/latest')
def api_casi_latest():
    """API lấy ca sĩ mới nhất"""
    result, error = db.execute_query("""
        SELECT idcasi, tencasi, Ngaysinh as ngaysinh, Sunghiep as sunghiep,
               DATE_FORMAT(created_at, '%%d/%%m/%%Y') as ngay_them
        FROM casi
        ORDER BY created_at DESC
        LIMIT 5
    """)
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result or [])


@main_bp.route('/api/bannhac/noibat')
def api_bannhac_noibat():
    """API lấy bản nhạc nổi bật"""
    result, error = db.execute_query("""
        SELECT b.idbannhac, b.tenbannhac, n.tennhacsi,
               COUNT(ba.idbanthuam) as soluong_banthuam,
               DATE_FORMAT(b.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM bannhac b
        JOIN nhacsi n ON b.idnhacsi = n.idnhacsi
        LEFT JOIN banthuam ba ON b.idbannhac = ba.idbannhac
        GROUP BY b.idbannhac
        ORDER BY soluong_banthuam DESC
        LIMIT 4
    """)
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result or [])


@main_bp.route('/api/banthuam/noibat')
def api_banthuam_noibat():
    """API lấy bản thu âm nổi bật"""
    result, error = db.execute_query("""
        SELECT ba.idbanthuam, ba.ngaythuam, bn.tenbannhac, c.tencasi,
               DATE_FORMAT(ba.created_at, '%%d/%%m/%%Y') as ngay_them
        FROM banthuam ba
        JOIN bannhac bn ON ba.idbannhac = bn.idbannhac
        JOIN casi c ON ba.idcasi = c.idcasi
        ORDER BY ba.created_at DESC
        LIMIT 6
    """)
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result or [])

@main_bp.route('/dashboard/progress')
def student_progress():
    """Trang theo dõi tiến độ học tập"""
    return render_template('dashboard/student_progress.html')