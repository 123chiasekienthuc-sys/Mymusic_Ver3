# application/middleware/logging.py
import time
import logging
from flask import g, request

logger = logging.getLogger(__name__)


def log_request():
    """Log thông tin request"""
    g.start = time.time()
    
    def log_after_request(response):
        elapsed = time.time() - g.start
        logger.info(f"{request.method} {request.path} completed in {elapsed:.3f}s with status {response.status_code}")
        return response
    
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append(log_after_request)