# application/services/init_database.py
import os
import logging
from application.services.database_service import DatabaseService

logger = logging.getLogger(__name__)
db = DatabaseService()


def init_user_tables():
    """Khởi tạo bảng quản lý người dùng"""
    logger.info("🔄 Đang kiểm tra và khởi tạo bảng quản lý người dùng...")
    
    try:
        # 1. Tạo bảng roles
        create_roles_table = """
        CREATE TABLE IF NOT EXISTS roles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        db.execute_query(create_roles_table)
        
        # 2. Tạo bảng users
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            avatar VARCHAR(255),
            role_id INT DEFAULT 2,
            is_active BOOLEAN DEFAULT TRUE,
            last_login TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL,
            INDEX idx_username (username),
            INDEX idx_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        db.execute_query(create_users_table)
        
        # 3. Tạo bảng user_sessions
        create_sessions_table = """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            session_token VARCHAR(255) NOT NULL UNIQUE,
            ip_address VARCHAR(45),
            user_agent TEXT,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_token (session_token),
            INDEX idx_expires (expires_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        db.execute_query(create_sessions_table)
        
        # 4. Tạo bảng user_activity
        create_activity_table = """
        CREATE TABLE IF NOT EXISTS user_activity (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            action VARCHAR(100) NOT NULL,
            details TEXT,
            ip_address VARCHAR(45),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user (user_id),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        db.execute_query(create_activity_table)
        
        # 5. Insert dữ liệu mặc định cho roles
        insert_roles = """
        INSERT IGNORE INTO roles (id, name, description) VALUES 
        (1, 'admin', 'Quản trị viên toàn quyền'),
        (2, 'user', 'Người dùng thông thường'),
        (3, 'editor', 'Biên tập viên, có thể thêm/sửa dữ liệu')
        """
        db.execute_query(insert_roles)
        
        # 6. Kiểm tra tài khoản admin
        from werkzeug.security import generate_password_hash
        check_admin = "SELECT id FROM users WHERE username = 'admin'"
        result, _ = db.execute_query(check_admin, fetch_one=True)
        
        if not result:
            admin_password = generate_password_hash('admin123')
            insert_admin = """
            INSERT INTO users (username, email, password_hash, full_name, role_id) 
            VALUES ('admin', 'admin@mymusic.com', %s, 'Quản trị viên', 1)
            """
            db.execute_query(insert_admin, (admin_password,))
            logger.info("✅ Đã tạo tài khoản admin mặc định (admin / admin123)")
        
        logger.info("✅ Khởi tạo bảng quản lý người dùng hoàn tất")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi khởi tạo bảng người dùng: {e}")


def init_exercise_tables():
    """Khởi tạo bảng bài tập"""
    logger.info("🔄 Đang kiểm tra và khởi tạo bảng bài tập...")
    
    try:
        # 1. Tạo bảng exercises
        create_exercises_table = """
        CREATE TABLE IF NOT EXISTS exercises (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) NOT NULL UNIQUE,
            level INT DEFAULT 1,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            requirements JSON,
            website_link VARCHAR(255),
            hint TEXT,
            solution TEXT,
            explanation TEXT,
            default_query TEXT,
            skill VARCHAR(50),
            topic VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            sort_order INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_code (code),
            INDEX idx_level (level),
            INDEX idx_skill (skill),
            INDEX idx_topic (topic)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        db.execute_query(create_exercises_table)
        
        # 2. Tạo bảng exercise_results
        create_results_table = """
        CREATE TABLE IF NOT EXISTS exercise_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            exercise_id INT NOT NULL,
            user_sql TEXT,
            is_correct BOOLEAN DEFAULT FALSE,
            feedback TEXT,
            execution_time FLOAT DEFAULT 0,
            error_message TEXT,
            ip_address VARCHAR(45),
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
            INDEX idx_exercise (exercise_id),
            INDEX idx_executed (executed_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        db.execute_query(create_results_table)
        
        # 3. Kiểm tra số lượng bài tập
        count_query = "SELECT COUNT(*) as count FROM exercises WHERE is_active = TRUE"
        result, _ = db.execute_query(count_query, fetch_one=True)
        exercise_count = result['count'] if result else 0
        
        if exercise_count == 0:
            logger.info("📝 Đang thêm dữ liệu bài tập mẫu...")
            insert_sample_exercises()
        
        logger.info("✅ Khởi tạo bảng bài tập hoàn tất")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi khởi tạo bảng bài tập: {e}")


def insert_sample_exercises():
    """Thêm dữ liệu bài tập mẫu"""
    
    sample_exercises = [
        {
            'code': 'BT1.1',
            'level': 1,
            'title': 'Khám phá trang danh sách nhạc sĩ',
            'description': 'Truy cập trang /nhacsi và viết câu lệnh SQL để lấy toàn bộ thông tin nhạc sĩ.',
            'requirements': ['Hiển thị tất cả các cột từ bảng nhacsi'],
            'website_link': '/nhacsi',
            'hint': 'Sử dụng SELECT * FROM nhacsi',
            'solution': 'SELECT * FROM nhacsi;',
            'explanation': '- SELECT * : lấy tất cả các cột\n- FROM nhacsi: từ bảng nhacsi',
            'default_query': 'SELECT * FROM nhacsi;',
            'skill': 'select',
            'topic': 'nhacsi'
        },
        {
            'code': 'BT1.2',
            'level': 1,
            'title': 'Khám phá trang danh sách ca sĩ',
            'description': 'Truy cập trang /casi và viết câu lệnh SQL để lấy toàn bộ thông tin ca sĩ.',
            'requirements': ['Hiển thị tất cả các cột từ bảng casi'],
            'website_link': '/casi',
            'hint': 'Sử dụng SELECT * FROM casi',
            'solution': 'SELECT * FROM casi;',
            'explanation': '- SELECT * : lấy tất cả các cột\n- FROM casi: từ bảng casi',
            'default_query': 'SELECT * FROM casi;',
            'skill': 'select',
            'topic': 'casi'
        },
        {
            'code': 'BT2.1',
            'level': 2,
            'title': 'Liệt kê bản nhạc kèm tên nhạc sĩ',
            'description': 'Trang /bannhac hiển thị tên bản nhạc và tên nhạc sĩ. Viết SQL để lấy thông tin này.',
            'requirements': ['Hiển thị: tenbannhac, tennhacsi', 'Sắp xếp theo tên bản nhạc A-Z'],
            'website_link': '/bannhac',
            'hint': 'Cần JOIN hai bảng bannhac và nhacsi qua idnhacsi',
            'solution': 'SELECT b.tenbannhac, n.tennhacsi FROM bannhac b JOIN nhacsi n ON b.idnhacsi = n.idnhacsi ORDER BY b.tenbannhac;',
            'explanation': '- JOIN: kết hợp hai bảng\n- ON: điều kiện kết nối\n- ORDER BY: sắp xếp',
            'default_query': 'SELECT b.tenbannhac, n.tennhacsi FROM bannhac b JOIN nhacsi n ON b.idnhacsi = n.idnhacsi LIMIT 10;',
            'skill': 'join',
            'topic': 'bannhac'
        },
        {
            'code': 'BT3.1',
            'level': 3,
            'title': 'Thống kê số bản thu âm theo ca sĩ',
            'description': 'Xem trang /casi, viết SQL đếm số bản thu âm của mỗi ca sĩ.',
            'requirements': ['Hiển thị: tencasi, so_luong_banthuam', 'Sắp xếp theo số lượng giảm dần'],
            'website_link': '/casi',
            'hint': 'Sử dụng LEFT JOIN và GROUP BY để đếm',
            'solution': 'SELECT c.tencasi, COUNT(bt.idbanthuam) as so_luong FROM casi c LEFT JOIN banthuam bt ON c.idcasi = bt.idcasi GROUP BY c.tencasi ORDER BY so_luong DESC;',
            'explanation': '- LEFT JOIN: lấy tất cả ca sĩ\n- COUNT: đếm số bản thu\n- GROUP BY: nhóm theo ca sĩ',
            'default_query': 'SELECT c.tencasi, COUNT(bt.idbanthuam) as so_luong FROM casi c LEFT JOIN banthuam bt ON c.idcasi = bt.idcasi GROUP BY c.tencasi LIMIT 10;',
            'skill': 'group',
            'topic': 'casi'
        },
        {
            'code': 'BT4.1',
            'level': 4,
            'title': 'Top 3 ca sĩ có nhiều bản thu âm nhất',
            'description': 'Tìm 3 ca sĩ có nhiều bản thu âm nhất.',
            'requirements': ['Hiển thị: tencasi, so_luong_banthuam', 'Chỉ lấy 3 ca sĩ đầu tiên'],
            'website_link': '/casi',
            'hint': 'Sử dụng ORDER BY và LIMIT',
            'solution': 'SELECT c.tencasi, COUNT(bt.idbanthuam) as so_luong FROM casi c LEFT JOIN banthuam bt ON c.idcasi = bt.idcasi GROUP BY c.tencasi ORDER BY so_luong DESC LIMIT 3;',
            'explanation': '- LIMIT 3: chỉ lấy 3 bản ghi đầu tiên\n- ORDER BY DESC: sắp xếp giảm dần',
            'default_query': 'SELECT c.tencasi, COUNT(bt.idbanthuam) as so_luong FROM casi c LEFT JOIN banthuam bt ON c.idcasi = bt.idcasi GROUP BY c.tencasi ORDER BY so_luong DESC LIMIT 3;',
            'skill': 'group',
            'topic': 'casi'
        }
    ]
    
    for ex in sample_exercises:
        import json
        query = """
            INSERT IGNORE INTO exercises 
            (code, level, title, description, requirements, website_link, 
             hint, solution, explanation, default_query, skill, topic)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            ex['code'], ex['level'], ex['title'], ex['description'],
            json.dumps(ex['requirements']), ex['website_link'],
            ex['hint'], ex['solution'], ex['explanation'],
            ex['default_query'], ex['skill'], ex['topic']
        )
        db.execute_query(query, params)
    
    logger.info(f"✅ Đã thêm {len(sample_exercises)} bài tập mẫu")


def init_all_tables():
    """Khởi tạo tất cả bảng"""
    init_user_tables()
    init_exercise_tables()