# application/middleware/__init__.py
from application.middleware.compression import compress_response
from application.middleware.logging import log_request

__all__ = ['compress_response', 'log_request']