# application/middleware/compression.py
import io
import gzip
import logging
from flask import request

logger = logging.getLogger(__name__)


def should_compress(response):
    """Kiểm tra có nên nén response không"""
    # Không nén ảnh, video
    content_type = response.headers.get('Content-Type', '')
    if 'image' in content_type or 'video' in content_type:
        return False
    
    # Chỉ nén response > 1KB
    if len(response.get_data()) < 1024:
        return False
    
    return True


def gzip_response(response):
    """Nén response bằng gzip"""
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding.lower():
        return response
    
    try:
        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(mode='wb', fileobj=gzip_buffer, compresslevel=6) as gz_file:
            gz_file.write(response.get_data())
        
        compressed_data = gzip_buffer.getvalue()
        
        # Chỉ nén nếu kích thước giảm
        if len(compressed_data) < len(response.get_data()):
            response.set_data(compressed_data)
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = len(compressed_data)
            response.headers['Vary'] = 'Accept-Encoding'
    except Exception as e:
        logger.error(f"Compression error: {e}")
    
    return response


def compress_response(response):
    """Middleware nén response"""
    if should_compress(response):
        return gzip_response(response)
    return response