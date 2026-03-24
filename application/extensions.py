# application/extensions.py
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from flask_login import LoginManager

csrf = CSRFProtect()
cors = CORS()
login_manager = LoginManager()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục'
login_manager.login_message_category = 'warning'