-- =============================================
-- TẠO CƠ SỞ DỮ LIỆU CHO HỆ THỐNG BÀI TẬP
-- =============================================

-- Bảng exercises - lưu thông tin bài tập
CREATE TABLE IF NOT EXISTS exercises (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    level INT NOT NULL CHECK (level IN (1,2,3,4)),
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_level (level),
    INDEX idx_skill (skill),
    INDEX idx_topic (topic),
    INDEX idx_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bảng exercise_results - lưu kết quả thực hành của học sinh
CREATE TABLE IF NOT EXISTS exercise_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exercise_id INT NOT NULL,
    user_id INT DEFAULT NULL,
    user_sql TEXT,
    is_correct BOOLEAN DEFAULT FALSE,
    feedback TEXT,
    execution_time FLOAT,
    rows_affected INT,
    error_message TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
    INDEX idx_exercise (exercise_id),
    INDEX idx_user (user_id),
    INDEX idx_executed (executed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bảng exercise_categories - phân loại bài tập
CREATE TABLE IF NOT EXISTS exercise_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    parent_id INT DEFAULT NULL,
    sort_order INT DEFAULT 0,
    
    FOREIGN KEY (parent_id) REFERENCES exercise_categories(id) ON DELETE CASCADE,
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bảng exercise_feedback - phản hồi chi tiết từ AI
CREATE TABLE IF NOT EXISTS exercise_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    result_id INT NOT NULL,
    score INT CHECK (score BETWEEN 0 AND 100),
    syntax_correct BOOLEAN,
    logic_correct BOOLEAN,
    efficiency_rating INT CHECK (efficiency_rating BETWEEN 1 AND 5),
    suggestions TEXT,
    ai_analysis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (result_id) REFERENCES exercise_results(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tạo view thống kê
CREATE OR REPLACE VIEW exercise_statistics AS
SELECT 
    e.level,
    e.skill,
    e.topic,
    COUNT(DISTINCT e.id) AS total_exercises,
    COUNT(DISTINCT er.id) AS total_attempts,
    AVG(CASE WHEN er.is_correct THEN 1 ELSE 0 END) * 100 AS success_rate,
    AVG(er.execution_time) AS avg_execution_time
FROM exercises e
LEFT JOIN exercise_results er ON e.id = er.exercise_id
GROUP BY e.level, e.skill, e.topic;