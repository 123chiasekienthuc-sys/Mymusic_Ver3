# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Cấu hình database
DB_CONFIG = {

    'host': os.getenv('MYSQLHOST', 'interchange.proxy.rlwy.net'),
    'user': os.getenv('MYSQLUSER', 'root'),
    'password': os.getenv('MYSQLPASSWORD', 'FJLMQpLSJZgzdwGTIOloLGzBCOypNCqz'),
    'database': os.getenv('MYSQLDATABASE', 'railway'),
    'port': int(os.getenv('MYSQLPORT', 58957)),
    'charset': 'utf8mb4',
    'use_unicode': True,
    'connect_timeout': 10,
    'autocommit': True
}


class Config:
    """Cấu hình cơ bản"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    DB_CONFIG = DB_CONFIG
    
    # Session
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600
    
    # Upload
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'aac', 'm4a'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Paths - QUAN TRỌNG: SỬA LẠI ĐƯỜNG DẪN
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.join(BASE_DIR, 'static')
    TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')  # Đây là thư mục templates gốc
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    # Upload folders
    SINGER_IMAGE_FOLDER = os.path.join(STATIC_DIR, 'images', 'singers')
    ARTIST_IMAGE_FOLDER = os.path.join(STATIC_DIR, 'images', 'artists')
    UPLOAD_FOLDER = os.path.join(STATIC_DIR, 'recordings')
    
    # Cache
    CACHE_TIMEOUT = 300
    CONNECTION_POOL_SIZE = 10
    
    # Pagination
    ITEMS_PER_PAGE = 12


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}