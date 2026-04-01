# application/controllers/__init__.py
from application.controllers.main_controller import main_bp
from application.controllers.auth_controller import auth_bp
from application.controllers.composer_controller import composer_bp
from application.controllers.singer_controller import singer_bp
from application.controllers.song_controller import song_bp
from application.controllers.recording_controller import recording_bp
from application.controllers.exercise_controller import exercise_bp
from application.controllers.ai_controller import ai_bp
from application.controllers.admin_controller import admin_bp

__all__ = [
    'main_bp', 
    'auth_bp', 
    'composer_bp', 
    'singer_bp', 
    'song_bp', 
    'recording_bp', 
    'exercise_bp', 
    'ai_bp', 
    'admin_bp'
]