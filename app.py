# app.py (mới)
import os
import sys
import logging

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Thêm đường dẫn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application import create_app
from config import Config

# Tạo app
app = create_app(os.getenv('FLASK_ENV', 'development'))

# app.py
from flask_login import logout_user


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = Config.DEBUG
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting server on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)