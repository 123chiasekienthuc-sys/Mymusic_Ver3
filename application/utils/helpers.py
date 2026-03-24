# application/utils/helpers.py
import os
import time
import logging
from functools import wraps
from flask import render_template, request, g, current_app
from config import Config

logger = logging.getLogger(__name__)


def create_directories():
    """Tạo các thư mục cần thiết"""
    directories = [
        Config.STATIC_DIR,
        Config.TEMPLATE_DIR,
        Config.DATA_DIR,
        Config.SINGER_IMAGE_FOLDER,
        Config.ARTIST_IMAGE_FOLDER,
        Config.UPLOAD_FOLDER
    ]
    
    for dir_path in directories:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            logger.warning(f"Cannot create {dir_path}: {e}")


def allowed_file(filename):
    """Kiểm tra file âm thanh hợp lệ"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_AUDIO_EXTENSIONS


def allowed_image(filename):
    """Kiểm tra file ảnh hợp lệ"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS


def utility_processor():
    """Context processor cho templates"""
    from flask_login import current_user
    
    class SafeUser:
        def __init__(self, user):
            self._user = user
            self._is_authenticated = user is not None and user.is_authenticated if hasattr(user, 'is_authenticated') else False
        
        @property
        def is_authenticated(self):
            return self._is_authenticated
        
        def __getattr__(self, name):
            if self._user and self._is_authenticated:
                return getattr(self._user, name, None)
            return None
        
        def is_admin(self):
            if self._user and self._is_authenticated and hasattr(self._user, 'is_admin'):
                return self._user.is_admin()
            return False
        
        def is_editor(self):
            if self._user and self._is_authenticated and hasattr(self._user, 'is_editor'):
                return self._user.is_editor()
            return False
    
    from datetime import datetime
    safe_user = SafeUser(current_user)
    
    return {
        'now': datetime.now,
        'current_user': safe_user,
        'is_authenticated': safe_user.is_authenticated,
        'is_admin': safe_user.is_admin,
        'is_editor': safe_user.is_editor,
    }


def not_found(error):
    """Error handler 404"""
    return render_template('404.html'), 404


def internal_error(error):
    """Error handler 500"""
    logger.error(f"Internal error: {error}")
    return render_template('500.html'), 500


def log_request_time():
    """Middleware để log thời gian request"""
    if hasattr(g, 'start'):
        elapsed = time.time() - g.start
        logger.info(f"Request to {request.path} took {elapsed:.3f}s")