# application/__init__.py
import os
import sys
from pathlib import Path
from flask import Flask

from config import config_by_name, Config
from application.extensions import csrf, cors, login_manager
from application.utils.helpers import create_directories
from application.controllers.auth_controller import auth_bp


def create_app(config_name='default'):
    """Factory function để tạo Flask app"""
    
    # In ra đường dẫn để debug
    #print(f"Template directory: {Config.TEMPLATE_DIR}")
    #print(f"Static directory: {Config.STATIC_DIR}")
    #print(f"Does template dir exist: {os.path.exists(Config.TEMPLATE_DIR)}")
    
    # Liệt kê các file trong thư mục templates
    #if os.path.exists(Config.TEMPLATE_DIR):
    #    print("Files in templates:")
    #    for file in os.listdir(Config.TEMPLATE_DIR):
    #        print(f"  - {file}")
    
    app = Flask(
        __name__,
        template_folder=Config.TEMPLATE_DIR,
        static_folder=Config.STATIC_DIR
    )
    
    app.config.from_object(config_by_name[config_name])
    
    csrf.init_app(app)
    cors.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    create_directories()
    register_blueprints(app)
    register_middleware(app)
    register_context_processors(app)
    register_error_handlers(app)
    init_services(app)
    
    return app


def register_blueprints(app):
    """Đăng ký tất cả blueprints"""
    from application.controllers import (
        main_bp, auth_bp, composer_bp, singer_bp,
        song_bp, recording_bp, exercise_bp, ai_bp, admin_bp, progress_bp
    )
    
    app.register_blueprint(main_bp)
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(composer_bp, url_prefix='/nhacsi')
    app.register_blueprint(singer_bp, url_prefix='/casi')
    app.register_blueprint(song_bp, url_prefix='/bannhac')
    app.register_blueprint(recording_bp, url_prefix='/banthuam')
    app.register_blueprint(exercise_bp, url_prefix='/api')
    app.register_blueprint(ai_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(progress_bp, url_prefix='/api/progress')

def register_middleware(app):
    """Đăng ký middleware"""
    from application.middleware.compression import compress_response
    app.after_request(compress_response)


def register_context_processors(app):
    """Đăng ký context processors"""
    from application.utils.helpers import utility_processor
    app.context_processor(utility_processor)


def register_error_handlers(app):
    """Đăng ký error handlers"""
    from application.utils.helpers import not_found, internal_error
    app.register_error_handler(404, not_found)
    app.register_error_handler(500, internal_error)


def init_services(app):
    """Khởi tạo các service"""
    from application.services.database_service import DatabaseService
    from application.services.cache_service import CacheService
    from application.services.init_database import init_all_tables
    
    with app.app_context():
        app.cache_service = CacheService(timeout=app.config.get('CACHE_TIMEOUT', 300))
        app.db_service = DatabaseService()
        
        if app.db_service.test_connection():
            app.logger.info("✅ Database connected")
            #init_all_tables()
        else:
            app.logger.warning("⚠️ Cannot connect to database")