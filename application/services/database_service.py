# application/services/database_service.py
import mysql.connector
from mysql.connector import Error
import logging
from config import Config

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service xử lý database operations"""
    
    def __init__(self):
        self.config = Config.DB_CONFIG
    
    def get_connection(self):
        """Tạo kết nối database"""
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def execute_query(self, query, params=None, fetch_one=False):
        """Thực thi query an toàn"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            if not conn:
                return None, "Không thể kết nối database"
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                if fetch_one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()
            else:
                conn.commit()
                result = {"affected_rows": cursor.rowcount}
            
            return result, None
            
        except Error as e:
            logger.error(f"Query error: {e}")
            return None, str(e)
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
    
    def test_connection(self):
        """Kiểm tra kết nối database"""
        conn = self.get_connection()
        if conn and conn.is_connected():
            conn.close()
            return True
        return False