# application/services/file_service.py
import os
import time
from werkzeug.utils import secure_filename
from config import Config


class FileService:
    """Service xử lý upload file"""
    
    @staticmethod
    def save_uploaded_file(file, folder, prefix='file'):
        """Lưu file upload"""
        if not file or not file.filename:
            return None
        
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        filename = secure_filename(f"{prefix}_{int(time.time())}.{ext}")
        save_path = os.path.join(folder, filename)
        file.save(save_path)
        return filename
    
    @staticmethod
    def delete_file(file_path):
        """Xóa file"""
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    
    @staticmethod
    def get_singer_image_path(filename):
        """Đường dẫn ảnh ca sĩ"""
        return os.path.join(Config.SINGER_IMAGE_FOLDER, filename) if filename else None
    
    @staticmethod
    def get_artist_image_path(filename):
        """Đường dẫn ảnh nhạc sĩ"""
        return os.path.join(Config.ARTIST_IMAGE_FOLDER, filename) if filename else None
    
    @staticmethod
    def get_recording_path(filename):
        """Đường dẫn file âm thanh"""
        return os.path.join(Config.UPLOAD_FOLDER, filename) if filename else None