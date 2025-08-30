"""
Utilities package for Super Simple Kiosk.

This package contains utility modules for input validation, logging configuration,
and other common functionality used throughout the application.
"""

from super_simple_kiosk.app.utils.logging import setup_logging
from super_simple_kiosk.app.utils.validators import validate_url

__all__ = ["setup_logging", "validate_url"]
