"""
API package for Super Simple Kiosk.

This package contains RESTful API endpoints for configuration management,
display control, URL management, and system management.
"""

from super_simple_kiosk.app.api.routes import bp
from super_simple_kiosk.app.api.schemas import (
    ConfigResponse,
    HealthResponse,
    StatusResponse,
    URLListResponse,
    URLResponse,
    create_error_response,
    create_success_response,
)

__all__ = [
    "ConfigResponse",
    "HealthResponse",
    "StatusResponse",
    "URLListResponse",
    "URLResponse",
    "bp",
    "create_error_response",
    "create_success_response",
]
