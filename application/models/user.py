# application/models/user.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from application.extensions import login_manager
from application.services.database_service import DatabaseService


class User(UserMixin):
    """Model người dùng cho Flask-Login"""
    
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.full_name = user_data.get('full_name')
        self.role_id = user_data.get('role_id', 2)
        self.avatar = user_data.get('avatar')
        self._is_active = user_data.get('is_active', True)
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
    
    @property
    def is_active(self):
        return self._is_active
    
    def is_admin(self):
        return self.role_id == 1
    
    def is_editor(self):
        return self.role_id == 3 or self.role_id == 1
    
    def get_role_name(self):
        roles = {1: 'admin', 2: 'user', 3: 'editor'}
        return roles.get(self.role_id, 'user')
    
    def get_id(self):
        return str(self.id)
    
    @staticmethod
    def create_password_hash(password):
        return generate_password_hash(password)
    
    @staticmethod
    def verify_password(password_hash, password):
        return check_password_hash(password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    """Load user từ database"""
    db = DatabaseService()
    query = "SELECT * FROM users WHERE id = %s AND is_active = TRUE"
    result, error = db.execute_query(query, (user_id,), fetch_one=True)
    
    if error or not result:
        return None
    return User(result)